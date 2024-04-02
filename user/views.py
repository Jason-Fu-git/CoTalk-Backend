from django.shortcuts import render
from utils.utils_require import require, CheckError, MAX_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, return_field)
from utils.utils_jwt import generate_jwt_token, verify_a_user, generate_salt
import json
import re
from .models import User, Friendship
from channels.layers import get_channel_layer
from ws.models import Client
from asgiref.sync import async_to_sync
from chat.models import Chat


@CheckError
def register(req: HttpRequest):
    """
    用户注册视图
    """
    if req.method != "POST":
        return BAD_METHOD

    body = json.loads(req.body.decode("utf-8"))

    user_name = require(body, "user_name", "string", err_msg="Missing or error type of [user_name]")
    password = require(body, "password", "string", err_msg="Missing or error type of [password]")
    user_email = require(body, "user_email", "string", err_msg="Missing or error type of [user_email]",
                         is_essential=False)
    description = require(body, "description", "string", err_msg="Missing or error type of [description]",
                          is_essential=False)
    avatar = require(body, "avatar", "string", err_msg="Missing or error type of [avatar]",
                     is_essential=False)  # todo:头像如何传输？

    # check validity of user_name , password, user_email and description
    if len(user_name) == 0 or len(user_name) > MAX_NAME_LENGTH:
        return BAD_REQUEST("Username length error")

    if len(password) == 0 or len(password) > MAX_NAME_LENGTH:
        return BAD_REQUEST("Password length error")

    if user_email is not None:
        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
            return BAD_REQUEST("Invalid email address")
        if len(user_email) == 0 or len(user_email) > MAX_EMAIL_LENGTH:
            return BAD_REQUEST("Email length error")

    if description is not None:
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return BAD_REQUEST("Description length error")

    # check user_name conflict
    if User.objects.filter(user_name=user_name).exists():
        return CONFLICT("Username conflict")  # 409
    else:
        user = User.objects.create(user_name=user_name, password=password)
        if user_email is not None:
            user.user_email = user_email
        if avatar is not None:
            user.user_icon = avatar
        if description is not None and len(description) > 0:
            user.description = description
        SALT = generate_salt()
        user.jwt_token_salt = SALT
        user.save()

        return request_success({
            "token": generate_jwt_token(SALT=SALT, user_id=user.user_id),
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_email": user.user_email,
            "description": user.description,
            "register_time": user.register_time,
            # "avatar": user.user_icon, # todo:handle avatar
        })


@CheckError
def login(req: HttpRequest):
    """
    用户登录视图
    """
    if req.method != "POST":
        return BAD_METHOD

    body = json.loads(req.body.decode("utf-8"))
    user_name = require(body, "user_name", "string", err_msg="Missing or error type of [user_name]")
    password = require(body, "password", "string", err_msg="Missing or error type of [password]")
    # todo : 后续添加2FA接口

    user = User.objects.filter(user_name=user_name)
    if user.exists():  # the user exists
        user = user.first()
        if user.password == password:  # login success
            SALT = generate_salt()
            user.jwt_token_salt = SALT
            user.save()
            return request_success({
                "token": generate_jwt_token(SALT=SALT, user_id=user.user_id),
                "user_id": user.user_id,
                "user_name": user.user_name,
                "user_email": user.user_email,
                "description": user.description,
                "register_time": user.register_time,
                # "avatar": user.user_icon, # todo: handle avatar
            })
        else:
            return UNAUTHORIZED("Unauthorized : Wrong password")  # 401
    else:
        return NOT_FOUND("User Not Found")  # 404


@CheckError
def user_management(req: HttpRequest, user_id):
    """
    用户详细信息获取/更新/删除视图
    :param req: HTTP请求
    :param user_id: url中的{user_id}
    """
    if req.method == "DELETE" or req.method == "PUT" or req.method == 'GET':

        try:
            user_id = int(user_id)
        except ValueError:
            return BAD_REQUEST("User id must be an integer")

        if User.objects.filter(user_id=user_id).exists():
            user = User.objects.get(user_id=user_id)
            SALT = user.jwt_token_salt

            if req.method == "GET":  # 获取用户信息
                return request_success(user.serialize())

            if verify_a_user(SALT=SALT, user_id=user.user_id, req=req):
                # todo : 添加2FA/密码验证
                # passed all security check, update user
                if req.method == "PUT":

                    body = json.loads(req.body.decode("utf-8"))

                    user_name = require(body, "user_name", is_essential=False)
                    password = require(body, "password", is_essential=False)
                    user_email = require(body, "user_email", is_essential=False)
                    description = require(body, "description", is_essential=False)
                    avatar = require(body, "avatar", is_essential=False)

                    # update
                    if user_name is not None:
                        if len(user_name) == 0 or len(user_name) > MAX_NAME_LENGTH:
                            return BAD_REQUEST("Username length error")
                        if User.objects.filter(user_name=user_name).exists():
                            return CONFLICT("Username conflict")
                        user.user_name = user_name

                    if password is not None:
                        if len(password) == 0 or len(password) > MAX_NAME_LENGTH:
                            return BAD_REQUEST("Password length error")
                        user.password = password

                    if user_email is not None:
                        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
                            return BAD_REQUEST("Invalid email address")
                        if len(user_email) == 0 or len(user_email) > MAX_EMAIL_LENGTH:
                            return BAD_REQUEST("Email length error")
                        user.user_email = user_email

                    if description is not None:
                        if len(description) == 0 or len(description) > MAX_DESCRIPTION_LENGTH:
                            return BAD_REQUEST("Description length error")
                        user.description = description

                    if avatar is not None:
                        user.avatar = avatar

                    user.save()
                else:
                    # passed all security check, delete user
                    user.delete()
                return request_success()
            else:
                return UNAUTHORIZED("Unauthorized : Verification failed")  # 401

        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD


@CheckError
def friend_management(req: HttpRequest, user_id):
    print(req.headers)
    if req.method == "GET" or req.method == "PUT":
        try:
            user_id = int(user_id)
        except ValueError:
            return BAD_REQUEST("User id must be an integer")

        if User.objects.filter(user_id=user_id).exists():
            user = User.objects.get(user_id=user_id)
            SALT = user.jwt_token_salt
            if verify_a_user(SALT=SALT, user_id=user.user_id, req=req):
                # verification passed
                if req.method == 'GET':
                    friends = User.objects.get(user_id=user_id).get_friends()
                    return request_success({
                        "friends": [
                            return_field(User.objects.get(user_id=friend['friend']).serialize(),
                                         ['user_id', 'user_name', 'user_email', 'description', 'register_time'])
                            for friend in friends
                        ]
                    })
                else:  # 'PUT'
                    body = json.loads(req.body.decode("utf-8"))

                    friend_id = require(body, 'friend_id', 'int')
                    approve = require(body, 'approve', 'bool', is_essential=False)
                    if approve is None:
                        approve = True

                    friend = User.objects.filter(user_id=friend_id)
                    if friend.exists():

                        # 尝试获取对应websocket
                        if Client.objects.filter(user_id=friend_id).exists():
                            channel_name = Client.objects.get(user_id=friend_id).channel_name
                        else:
                            channel_name = None

                        ABFriendship = Friendship.objects.filter(user_id=user_id, friend__user_id=friend_id)
                        BAFriendship = Friendship.objects.filter(user_id=friend_id, friend__user_id=user_id)
                        if BAFriendship.exists():
                            if ABFriendship.exists():
                                if not approve:  # 删除好友
                                    ABFriendship.delete()
                                    BAFriendship.delete()
                                    if channel_name is not None:
                                        async_to_sync(get_channel_layer().send)(
                                            channel_name, {
                                                'type': 'user.friend.request',
                                                'status': 'delete',
                                                'user_id': user_id,
                                                'is_approved': approve,
                                            })
                            else:  # 响应好友请求
                                if approve:  # 同意请求
                                    Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                              friend=User.objects.get(user_id=friend_id),
                                                              is_approved=True).save()
                                    BAFriendship = BAFriendship.first()
                                    BAFriendship.is_approved = True
                                    BAFriendship.save()
                                    if channel_name is not None:
                                        async_to_sync(get_channel_layer().send)(
                                            channel_name, {
                                                'type': 'user.friend.request',
                                                'status': 'accept request',
                                                'user_id': user_id,
                                                'is_approved': approve,
                                            })
                                else:  # 拒绝请求
                                    BAFriendship.delete()
                                    if channel_name is not None:
                                        async_to_sync(get_channel_layer().send)(
                                            channel_name, {
                                                'type': 'user.friend.request',
                                                'status': 'reject request',
                                                'user_id': user_id,
                                                'is_approved': approve,
                                            })
                        else:  # 发起请求
                            Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                      friend=User.objects.get(user_id=friend_id),
                                                      is_approved=False).save()  # 首次请求的APPROVE应该是False
                            if channel_name is not None:
                                async_to_sync(get_channel_layer().send)(
                                    channel_name, {
                                        'type': 'user.friend.request',
                                        'status': 'make request',
                                        'user_id': user_id,
                                        'is_approved': approve,
                                    })
                        return request_success()
                    else:
                        return NOT_FOUND('Invalid friend id')

            else:
                return UNAUTHORIZED("Unauthorized : Verification failed")  # 401
        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD


@CheckError
def search_for_users(req: HttpRequest):
    if req.method == 'GET':
        search_text = req.GET.get('search_text', None)
        if search_text is None or search_text == '':  # 搜索文字为空，返回所有用户
            users = User.objects.all()
        else:  # 根据搜索文本返回
            users = User.objects.filter(user_name__contains=search_text) | User.objects.filter(
                user_email__contains=search_text)
        return request_success({
            'users': [
                return_field(user.serialize(), ['user_id', 'user_name', 'user_email', 'description', 'register_time'])
                for user in users
            ]
        })
    else:
        return BAD_METHOD

# @CheckError
# def user_chats_management(req: HttpRequest, user_id):
#     if req.method == 'GET' or req.method == 'DELETE':
#
#         try:
#             user_id = int(user_id)
#         except ValueError:
#             return BAD_REQUEST("User id must be an integer")
#
#         if User.objects.filter(user_id=user_id).exists():
#             if verify_a_user(user_id, req):
#                 # verification passed
#                 user = User.objects.get(user_id=user_id)
#                 if req.method == 'GET':  # 获取聊天列表
#                     chats = user.get_chats()
#                     if len(chats) == 0:
#                         return request_success({'chats': []})
#                     else:
#                         return request_success({
#                             'chats': [
#                                 return_field(Chat.objects.get(chat_id=chat['chat']).serialize(),
#                                              ['chat_id', 'chat_name', 'is_private'])
#                                 for chat in chats]
#                         })
#
#             else:
#                 return UNAUTHORIZED("Unauthorized")  # 401
#         else:
#             return NOT_FOUND("Invalid user id")  # 404
#     else:
#         return BAD_METHOD
