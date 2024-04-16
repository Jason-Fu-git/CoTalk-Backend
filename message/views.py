from utils.utils_require import (require, CheckError, MAX_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH,
                                 NOT_FOUND_USER_ID, NOT_FOUND_CHAT_ID, UNAUTHORIZED_JWT, NOT_FOUND_MESSAGE_ID,
                                 NO_MANAGEMENT_PRIVILEGE, MAX_MESSAGE_LENGTH)
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, PRECONDITION_FAILED, return_field)
from utils.utils_jwt import generate_jwt_token, verify_a_user, generate_salt
from utils.utils_time import get_timestamp
import json
from user.models import User
from .models import Message, Notification
from chat.models import Chat, Membership
from ws.models import Client
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@CheckError
def message_management(req: HttpRequest, message_id):
    """
    消息的获取/删除/标记已读
    """

    if req.method != 'GET' and req.method != 'DELETE' and req.method != 'PUT':
        return BAD_METHOD  # 405

    try:
        message_id = int(message_id)
    except ValueError as e:
        return BAD_REQUEST("Invalid message id : Must be integer")  # 400

    user_id = require(req.GET, 'user_id', 'string', req=req)

    # user check
    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    if not verify_a_user(salt=user.jwt_token_salt, user_id=user_id, req=req):
        return UNAUTHORIZED(UNAUTHORIZED_JWT)  # 401

    # message check
    if not Message.objects.filter(message_id=message_id).exists():
        return NOT_FOUND(NOT_FOUND_MESSAGE_ID)  # 404

    message = Message.objects.get(message_id=message_id)

    # membership check
    if not Membership.objects.filter(chat_id=message.chat.chat_id, user_id=user_id, is_approved=True).exists():
        return UNAUTHORIZED("Unauthorized : the user cannot see the message")

    # unseen (delete) check
    if message.unable_to_see_users.filter(user_id=user_id).exists():
        return UNAUTHORIZED("Unauthorized : the user cannot see the message")

    # get
    if req.method == 'GET':
        return request_success(return_field(
            message.serialize(),
            ["code",
             "info",

             "msg_id",
             "sender_id",
             "chat_id",

             "msg_text",
             "msg_type",

             "create_time",
             "update_time",

             "read_users",
             "unable_to_see_users",

             "reply_to",
             "is_system",
             "msg_file_url"]
        ))
    # put
    elif req.method == 'PUT':
        if not message.read_users.filter(user_id=user_id).exists():
            message.read_users.add(user_id)
    # delete
    else:
        body = json.loads(req.body.decode('utf-8'))
        is_remove = require(body, 'is_remove', 'bool')
        if is_remove:  # 撤回
            # check privilege
            if user_id != message.sender_id:
                return UNAUTHORIZED("Unauthorized : the user is not the sender of the message")

            # check time
            if get_timestamp() + 300 > message.create_time:
                return PRECONDITION_FAILED("Precondition Failed : time exceed")

            # delete
            message.delete()
        else:  # 删除
            message.unable_to_see_users.add(user_id)

    return request_success()


@CheckError
def post_message(req: HttpRequest):
    """
    前端向后端发送消息
    """

    if req.method != 'POST':
        return BAD_METHOD  # 405

    user_id = require(req.POST, 'user_id', 'string', req=req)
    chat_id = require(req.POST, 'chat_id', 'string', req=req)
    msg_text = require(req.POST, 'msg_text', 'string', req=req)
    msg_type = require(req.POST, 'msg_type', 'string', req=req)

    # user check
    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    # chat check
    if not Chat.objects.filter(chat_id=chat_id).exists():
        return NOT_FOUND(NOT_FOUND_CHAT_ID)  # 404

    # membership check
    if not Membership.objects.filter(chat_id=chat_id, user_id=user_id, is_approved=True).exists():
        return UNAUTHORIZED(f"Unauthorized : user {user_id} not in chat {chat_id}")

    # verification

    user = User.objects.get(user_id=user_id)
    if not verify_a_user(salt=user.jwt_token_salt, user_id=user_id, req=req):
        return UNAUTHORIZED(UNAUTHORIZED_JWT)  # 401

    # get reply to
    reply_to = require(req.POST, 'reply_to', 'int', req=req)
    if reply_to is not None:
        if not Message.objects.filter(chat_id=chat_id, message_id=reply_to).exists():
            return NOT_FOUND("Not found : reply_to message not found")  # 404
        reply_to = Message.objects.get(chat_id=chat_id, message_id=reply_to)

    # check msg_length
    if len(msg_text) > MAX_MESSAGE_LENGTH:
        return BAD_REQUEST("Invalid msg_text : msg_text length exceed")  # 400

    # check msg_type
    if msg_type == 'text':
        message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='T')

        msg_file = require(req.FILES, 'msg_file', 'file')
        message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='')

    else:

        msg_file = require(req.FILES, 'msg_file', 'file')
        if msg_text == 'image':
            if msg_file.name.endswith('.png') or msg_file.name.endswith('.jpg') or msg_file.name.endswith('.jpeg'):
                message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='I',
                                                 msg_file=msg_file)
            else:
                return BAD_REQUEST(
                    "Invalid msg_file : msg_file type not supported, should be one of png, jpg, jpeg")  # 400

        elif msg_text == 'video':
            if msg_file.name.endswith('.mp4') or msg_file.name.endswith('.avi') or msg_file.name.endswith(
                    '.flv') or msg_file.name.endswith('.mkv'):
                message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='V',
                                                 msg_file=msg_file)
            else:
                return BAD_REQUEST(
                    "Invalid msg_file : msg_file type not supported, should be one of mp4, avi, flv, mkv")  # 400

        elif msg_type == 'audio':
            if msg_file.name.endswith('.mp3') or msg_file.name.endswith('.wav') or msg_file.name.endswith('.flac'):
                message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='A',
                                                 msg_file=msg_file)

            else:
                return BAD_REQUEST(
                    "Invalid msg_file : msg_file type not supported, should be one of mp3, wav, flac")  # 400

        else:
            message = Message.objects.create(sender_id=user_id, chat_id=chat_id, msg_text=msg_text, msg_type='O',
                                             msg_file=msg_file)

    if reply_to is not None:
        message.reply_to = reply_to.msg_id
        message.save()

    return request_success()
