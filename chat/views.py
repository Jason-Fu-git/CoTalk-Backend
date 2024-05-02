from utils.utils_require import (require, CheckError, MAX_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH,
                                 NOT_FOUND_USER_ID, NOT_FOUND_CHAT_ID, UNAUTHORIZED_JWT, NO_MANAGEMENT_PRIVILEGE)
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, PRECONDITION_FAILED, return_field)
from utils.utils_jwt import generate_jwt_token, verify_a_user, generate_salt
import json
from user.models import User
from .models import Chat, Membership
from message.models import Message, Notification, kick_a_person, join_a_chat, change_privilege
from ws.models import Client
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@CheckError
def create_a_chat(req: HttpRequest):
    """
    创建聊天视图
    """
    if req.method != 'POST':
        return BAD_METHOD  # 405

    body = json.loads(req.body.decode('utf-8'))

    user_id = require(body, 'user_id', 'int')
    chat_name = require(body, 'chat_name', 'string')
    members = require(body, 'members', 'array', is_essential=False)

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    verify_a_user(salt=user.jwt_token_salt, user_id=user_id, req=req)

    # verification passed
    if Chat.objects.filter(chat_name=chat_name).exists():
        return CONFLICT("Chat name conflict")
    # create a chat
    chat = Chat.objects.create(chat_name=chat_name, is_private=False)
    chat.save()
    # create a membership (Owner)
    membership = Membership.objects.create(user=user, chat=chat, privilege='O', is_approved=True)
    membership.save()
    # notify the members
    if members is not None:
        for member in members:
            notification_dict = {
                'type': 'chat.management',
                'status': 'make invitation',
                'user_id': user_id,
                'chat_id': chat.chat_id,
                'is_approved': True,
            }
            Membership.objects.create(user_id=member, chat_id=chat.chat_id, privilege='M', is_approved=False)
            # 动态websocket
            if Client.objects.filter(user_id=member).exists():
                channel_name = Client.objects.get(user_id=member).channel_name
                async_to_sync(get_channel_layer().send)(
                    channel_name,
                    notification_dict
                )
            # 静态notification
            else:
                Notification.objects.create(sender_id=user_id, receiver_id=member, content=str(notification_dict))

    return request_success({
        "chat_id": chat.chat_id,
        "create_time": chat.create_time
    })


@CheckError
def get_chat_detail(req: HttpRequest, chat_id):
    """
    获取一个聊天的聊天名、群主用户id、群成员数、创建时间、是否为私聊
    """
    if req.method != 'GET':
        return BAD_METHOD  # 405

    try:
        chat_id = int(chat_id)
    except ValueError:
        return BAD_REQUEST("Chat id must be an integer")  # 400

    if not Chat.objects.filter(chat_id=chat_id).exists():
        return NOT_FOUND(NOT_FOUND_CHAT_ID)  # 404

    chat = Chat.objects.get(chat_id=chat_id)
    return request_success({
        "chat_id": chat_id,
        "chat_name": chat.chat_name,
        "owner_id": chat.get_owner().user_id,
        "member_num": len(chat.get_memberships()),
        "create_time": chat.create_time,
        "is_private": chat.is_private,
    })


@CheckError
def chat_members(req: HttpRequest, chat_id):
    """
    聊天成员获取/邀请视图
    """
    if req.method != "GET" and req.method != "PUT":
        return BAD_METHOD  # 405

    try:
        chat_id = int(chat_id)
    except ValueError:
        return BAD_REQUEST("Chat id must be an integer")  # 400

    if req.content_type == "application/json":
        body = json.loads(req.body.decode('utf-8'))
        user_id = require(body, 'user_id', 'int')
    else:  # query string
        user_id = req.GET.get('user_id', None)

    if user_id is None:
        return BAD_REQUEST("User id is required")  # 400
    try:
        user_id = int(user_id)
    except ValueError:
        return BAD_REQUEST("User id must be an integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    SALT = user.jwt_token_salt
    verify_a_user(salt=SALT, user_id=user.user_id, req=req)

    if not Membership.objects.filter(user_id=user_id, chat_id=chat_id).exists():
        return NOT_FOUND('Invalid chat id or user not in chat')  # 404

    # verification passed
    if req.method == 'GET':
        # return the member list
        memberships = Chat.objects.get(chat_id=chat_id).get_memberships()
        return request_success({
            "members": [
                {
                    'user_id': membership.user.user_id,
                    'user_name': membership.user.user_name,
                    'user_email': membership.user.user_email,
                    'description': membership.user.description,
                    'register_time': membership.user.register_time,
                    'privilege': membership.privilege,
                }
                for membership in memberships
            ]
        })
    else:  # 'PUT'
        # invite/kick a member
        body = json.loads(req.body.decode("utf-8"))

        member_id = require(body, 'member_id', 'int')
        approve = require(body, 'approve', 'bool', is_essential=False)
        if approve is None:
            approve = True

        if not User.objects.filter(user_id=member_id).exists():
            return NOT_FOUND('Invalid member id')  # 404

        # 尝试获取对应websocket
        if Client.objects.filter(user_id=member_id).exists():
            channel_name = Client.objects.get(user_id=member_id).channel_name
        else:
            channel_name = None

        notification_dict = None
        # 判断请求情况
        if Membership.objects.filter(user_id=member_id, chat_id=chat_id).exists():
            membership = Membership.objects.get(user_id=member_id, chat_id=chat_id)
            if membership.is_approved:  # the user is already a member
                if not approve:  # kick him out
                    if Membership.objects.get(user_id=user_id, chat_id=chat_id).privilege != 'M' \
                            and membership.privilege != 'O':
                        # have privilege and the other user is not the owner
                        membership.delete()
                        # 新建系统消息
                        kick_a_person(admin_id=user_id, member_id=member_id, chat_id=chat_id)
                        # 新建系统通知
                        notification_dict = {
                            'type': 'chat.management',
                            'status': 'kicked out',
                            'user_id': user_id,
                            'chat_id': chat_id,
                            'is_approved': False
                        }
                    else:  # no privilege
                        return UNAUTHORIZED('Unauthorized: no management privilege')  # 400
            else:
                if user_id == member_id:  # accept / reject
                    if approve:  # accept invitation
                        membership.is_approved = True
                        membership.save()
                        # 新建系统消息
                        join_a_chat(user_id=user_id, chat_id=chat_id)
                    else:  # reject invitation
                        membership.delete()
                else:
                    return BAD_REQUEST('Invalid situation')  # 400

        else:  # make invitations
            Membership.objects.create(user_id=member_id, chat_id=chat_id, privilege='M',
                                      is_approved=False)
            # 新建系统通知
            notification_dict = {
                'type': 'chat.management',
                'status': 'make invitation',
                'user_id': user_id,
                'chat_id': chat_id,
                'is_approved': True
            }

        if notification_dict is not None:
            if channel_name is None:
                # 静态Notification
                Notification.objects.create(sender_id=user_id, receiver_id=member_id, content=str(notification_dict))
            else:
                # 动态websocket
                async_to_sync(get_channel_layer().send)(
                    channel_name,
                    notification_dict
                )
        return request_success()


@CheckError
def chat_management(req: HttpRequest, chat_id):
    """
    聊天成员权限更改视图
    """
    if req.method != 'PUT':
        return BAD_METHOD  # 405

    # change privilege
    try:
        chat_id = int(chat_id)
    except ValueError:
        return BAD_REQUEST("Chat id must be an integer")  # 400

    body = json.loads(req.body.decode('utf-8'))
    user_id = require(body, 'user_id', 'int')
    member_id = require(body, 'member_id', 'int')
    change_to = require(body, 'change_to', 'string')

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    if not Membership.objects.filter(user_id=user_id, chat_id=chat_id).exists():
        return NOT_FOUND("Invalid chat id or user not in chat")  # 404

    # Verification
    user_privilege = Membership.objects.get(user_id=user_id, chat_id=chat_id).privilege
    SALT = user.jwt_token_salt
    verify_a_user(salt=SALT, user_id=user.user_id, req=req)

    if not User.objects.filter(user_id=member_id).exists():
        return NOT_FOUND("Invalid member id")  # 404

    if not Membership.objects.filter(user_id=member_id, chat_id=chat_id).exists():
        return NOT_FOUND('Invalid chat id or member not in chat')  # 404

    membership = Membership.objects.get(user_id=member_id, chat_id=chat_id)
    if membership.privilege == 'O':  # no one can change the owner's privilege
        return UNAUTHORIZED(NO_MANAGEMENT_PRIVILEGE)  # 401

    # change privilege
    if change_to == 'member':
        # check privilege
        if user_privilege == 'O' or user_privilege == 'A':
            membership.privilege = 'M'
            membership.save()
        else:
            return UNAUTHORIZED(NO_MANAGEMENT_PRIVILEGE)  # 401
    elif change_to == 'admin':
        if user_privilege == 'O':
            if len(Chat.objects.get(chat_id=chat_id).get_admins()) == 3:
                return PRECONDITION_FAILED("There are already 3 admins")  # 412
            membership.privilege = 'A'
            membership.save()
        else:
            return UNAUTHORIZED(NO_MANAGEMENT_PRIVILEGE)  # 401
    elif change_to == 'owner':
        if user_privilege == 'O':
            membership.privilege = 'O'
            membership.save()
            # the former owner now becomes a member
            user_membership = Membership.objects.get(user_id=user_id, chat_id=chat_id)
            user_membership.privilege = 'M'
            user_membership.save()
        else:
            return UNAUTHORIZED(NO_MANAGEMENT_PRIVILEGE)  # 401
    else:
        return BAD_REQUEST(f'Invalid change_to parameter: {change_to}')  # 400

    # 新建系统消息
    change_privilege(admin_id=user_id, member_id=member_id, chat_id=chat_id, privilege=change_to)

    # 新建系统通知
    notification_dict = {
        'type': 'chat.management',
        'status': f'change to {change_to}',
        'user_id': user_id,
        'chat_id': chat_id,
        'is_approved': True
    }

    if Client.objects.filter(user_id=member_id).exists():
        channel_name = Client.objects.get(user_id=member_id).channel_name
        async_to_sync(get_channel_layer().send)(
            channel_name,
            notification_dict
        )
    else:
        Notification.objects.create(sender_id=user_id,
                                    receiver_id=member_id,
                                    content=str(notification_dict))

    return request_success()


@CheckError
def get_messages(req: HttpRequest, chat_id):
    if req.method != 'GET':
        return BAD_METHOD  # 405

    try:
        chat_id = int(chat_id)
    except ValueError as e:
        return BAD_REQUEST("Invalid chat id : Must be integer")  # 400

    user_id = require(req.GET, 'user_id', 'int', req=req)

    # user check
    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    # chat check
    if not Chat.objects.filter(chat_id=chat_id).exists():
        return NOT_FOUND(NOT_FOUND_CHAT_ID)

    user = User.objects.get(user_id=user_id)
    chat = Chat.objects.get(chat_id=chat_id)
    verify_a_user(salt=user.jwt_token_salt, user_id=user_id, req=req)

    # membership check
    if not Membership.objects.filter(chat_id=chat_id, user_id=user_id, is_approved=True).exists():
        return UNAUTHORIZED(f"Unauthorized : user {user_id} not in chat {chat_id}")

    messages = chat.get_messages(unable_to_see_user_id=user_id)

    # filter
    filter_info = "Success"
    filter_text = require(req.GET, 'filter_text', 'string', is_essential=False, req=req)

    if filter_text is not None:
        messages = messages.filter(msg_text__contains=filter_text)
        filter_info += ", filter_text: " + filter_text

    filter_user = require(req.GET, 'filter_user', 'int', is_essential=False, req=req)

    if filter_user is not None:
        messages = messages.filter(sender_id=filter_user)
        filter_info += ", filter_user: " + str(filter_user)

    filter_before = require(req.GET, 'filter_before', 'float', is_essential=False, req=req)

    if filter_before is not None:
        messages = messages.filter(create_time__lt=filter_before)
        filter_info += ", filter_before: " + str(filter_before)

    filter_after = require(req.GET, 'filter_after', 'float', is_essential=False, req=req)

    if filter_after is not None:
        messages = messages.filter(create_time__gt=filter_after)
        filter_info += ", filter_after: " + str(filter_after)

    return request_success({
        "messages": [
            return_field(
                message.serialize(),
                [
                    "msg_id",
                    "sender_id",
                    "chat_id",

                    "msg_text",
                    "msg_type",

                    "create_time",
                    "update_time",

                    "read_users",

                    "reply_to",
                    "is_system",
                    "msg_file_url"]
            ) for message in messages
        ]
    }, info=filter_info)
