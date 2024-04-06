from utils.utils_require import require, CheckError, MAX_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, PRECONDITION_FAILED, return_field)
from utils.utils_jwt import generate_jwt_token, verify_a_user, generate_salt
import json
from user.models import User
from .models import Chat, Membership
from ws.models import Client
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


@CheckError
def create_a_chat(req: HttpRequest):
    if req.method == 'POST':

        body = json.loads(req.body.decode('utf-8'))

        user_id = require(body, 'user_id', 'int')
        chat_name = require(body, 'chat_name', 'string')
        members = require(body, 'members', 'array')

        if User.objects.filter(user_id=user_id).exists():
            user = User.objects.get(user_id=user_id)
            if verify_a_user(SALT=user.jwt_token_salt, user_id=user_id, req=req):
                # verification passed
                if Chat.objects.filter(chat_name=chat_name).exists():
                    return CONFLICT("Chat name conflict")
                # create a chat
                chat = Chat.objects.create(chat_name=chat_name)
                chat.save()
                # create a membership (Owner)
                membership = Membership.objects.create(user=user, chat=chat, privilege='O')
                membership.save()
                # notify the members
                if members is not None:
                    for member in members:
                        # todo : use websocket to send notification
                        print(member)
                return request_success({
                    "chat_id": chat.chat_id,
                    "create_time": chat.create_time
                })
            else:
                return UNAUTHORIZED("Unauthorized")  # 401
        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD


@CheckError
def chat_members(req: HttpRequest, chat_id):
    if req.method == "GET" or req.method == "PUT":
        try:
            chat_id = int(chat_id)
        except ValueError:
            return BAD_REQUEST("Chat id must be an integer")

        body = json.loads(req.body.decode('utf-8'))
        user_id = require(body, 'user_id', 'int')

        if User.objects.filter(user_id=user_id).exists():
            user = User.objects.get(user_id=user_id)
            SALT = user.jwt_token_salt
            if verify_a_user(SALT=SALT, user_id=user.user_id, req=req):
                if Membership.objects.filter(user_id=user_id, chat_id=chat_id).exists():
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
                                    # 'avatar'
                                }
                                for membership in memberships
                            ]
                        })
                    else:  # 'PUT'
                        # invite/kick a member
                        body = json.loads(req.body.decode("utf-8"))

                        user_id = require(body, 'user_id', 'int')
                        member_id = require(body, 'member_id', 'int')
                        approve = require(body, 'approve', 'bool', is_essential=False)
                        if approve is None:
                            approve = True

                        member = User.objects.filter(user_id=member_id)
                        if member.exists():

                            # 尝试获取对应websocket
                            if Client.objects.filter(user_id=member_id).exists():
                                channel_name = Client.objects.get(user_id=member_id).channel_name
                            else:
                                channel_name = None

                            if Membership.objects.filter(user_id=member_id, chat_id=chat_id).exists():
                                membership = Membership.objects.get(user_id=member_id, chat_id=chat_id)
                                if membership.is_approved:  # the user is already a member
                                    if not approve:  # kick him out
                                        if Membership.objects.get(user_id=user_id, chat_id=chat_id).privilege != 'M' \
                                                and membership.privilege != 'O':
                                            # have privilege and the other user is not the owner
                                            membership.delete()
                                            if channel_name is not None:
                                                async_to_sync(get_channel_layer().send)(
                                                    channel_name, {
                                                        'type': 'chat.members.request',
                                                        'status': 'delete',
                                                        'user_id': user_id,
                                                        'is_approved': approve,
                                                    })
                                        else:  # no privilege
                                            return NOT_FOUND('Unauthorized: no management privilege')
                                else:
                                    if user_id == member_id:  # accept / reject
                                        if approve:  # accept invitation
                                            membership.is_approved = True
                                            membership.save()
                                            # todo : broadcast to all the members
                                        else:  # reject invitation
                                            membership.delete()
                                    else:
                                        return BAD_REQUEST('Invalid situation')

                            else:  # make invitations
                                Membership.objects.create(user_id=member_id, chat_id=chat_id, privilege='M',
                                                          is_approved=False)
                                if channel_name is not None:
                                    async_to_sync(get_channel_layer().send)(
                                        channel_name, {
                                            'type': 'chat.members.request',
                                            'status': 'make request',
                                            'user_id': user_id,
                                            'is_approved': approve,
                                        })
                            return request_success()
                        else:
                            return NOT_FOUND('Invalid member id')  # 404
                else:
                    return NOT_FOUND('Invalid chat id or user not in chat')  # 404
            else:
                return UNAUTHORIZED("Unauthorized : Verification failed")  # 401

        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD


@CheckError
def chat_management(req: HttpRequest, chat_id):
    if req.method == 'PUT':
        # change privilege
        try:
            chat_id = int(chat_id)
        except ValueError:
            return BAD_REQUEST("Chat id must be an integer")

        body = json.loads(req.body.decode('utf-8'))
        user_id = require(body, 'user_id', 'int')
        member_id = require(body, 'member_id', 'int')
        change_to = require(body, 'change_to', 'string')

        if User.objects.filter(user_id=user_id).exists():
            user = User.objects.get(user_id=user_id)
            if not Membership.objects.filter(user_id=user_id, chat_id=chat_id).exists():
                return NOT_FOUND("Invalid chat id or user not in chat")
            user_privilege = Membership.objects.get(user_id=user_id, chat_id=chat_id).privilege
            SALT = user.jwt_token_salt
            if verify_a_user(SALT=SALT, user_id=user.user_id, req=req):
                if User.objects.filter(user_id=member_id).exists():
                    if not Membership.objects.filter(user_id=member_id, chat_id=chat_id).exists():
                        return NOT_FOUND('Invalid chat id or member not in chat')
                    membership = Membership.objects.get(user_id=member_id, chat_id=chat_id)
                    if change_to == 'member':
                        # check privilege
                        if user_privilege == 'O' or user_privilege == 'A':
                            membership.privilege = 'M'
                            membership.save()
                            # todo : use websocket
                        else:
                            return UNAUTHORIZED('No management privilege')
                    elif change_to == 'admin':
                        if user_privilege == 'O':
                            if len(Chat.objects.get(chat_id=chat_id).get_admins()) == 3:
                                return PRECONDITION_FAILED("There are already 3 admins")
                            membership.privilege = 'A'
                            membership.save()
                            # todo: use websocket
                        else:
                            return UNAUTHORIZED('No management privilege')
                    elif change_to == 'owner':
                        if user_privilege == 'O':
                            membership.privilege = 'O'
                            membership.save()
                            # the former owner now becomes a member
                            user_membership = Membership.objects.get(user_id=user_id, chat_id=chat_id)
                            user_membership.privilege = 'M'
                            user_membership.save()
                            # todo: use websocket
                        else:
                            return UNAUTHORIZED('No management privilege')
                    else:
                        return BAD_REQUEST(f'Invalid change_to parameter: {change_to}')
                    return request_success()
                else:
                    return NOT_FOUND("Invalid member id")
            else:
                return UNAUTHORIZED("Unauthorized : Verification failed")

        else:
            return NOT_FOUND('Invalid user id')
    else:
        return BAD_METHOD
