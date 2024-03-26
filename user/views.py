from django.shortcuts import render
from utils.utils_require import require, CheckError
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, return_field)
from utils.utils_jwt import generate_jwt_token, verify_a_user
import json
import re
from .models import User, Friendship


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
    avatar = require(body, "avatar", "string", err_msg="Missing or error type of [avatar]",
                     is_essential=False)  # todo:头像如何传输？

    # check validity of user_name , password and user_email
    if len(user_name) == 0 or len(user_name) > 50:
        return BAD_REQUEST("Username length error")

    if len(password) == 0 or len(password) > 50:
        return BAD_REQUEST("Password length error")

    if user_email is not None:
        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
            return BAD_REQUEST("Invalid email address")

    # check user_name conflict
    if User.objects.filter(user_name=user_name).exists():
        return CONFLICT("Username conflict")  # 409
    else:
        user = User.objects.create(user_name=user_name, password=password)
        if user_email is not None:
            user.user_email = user_email
        if avatar is not None:
            user.user_icon = avatar
        user.save()
        return request_success({
            "token": generate_jwt_token(user_id=user.user_id),
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_email": user.user_email,
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
            return request_success({
                "token": generate_jwt_token(user_id=user.user_id),
                "user_id": user.user_id,
                "user_name": user.user_name,
                "user_email": user.user_email,
                # "avatar": user.user_icon, # todo: handle avatar
            })
        else:
            return UNAUTHORIZED("Wrong password")  # 401
    else:
        return NOT_FOUND("User Not Found")  # 404


@CheckError
def update_or_delete(req: HttpRequest, user_id):
    """
    用户更新/删除视图
    :param req: HTTP请求
    :param user_id: url中的{user_id}
    """
    if req.method == "DELETE" or req.method == "PUT":

        user = User.objects.filter(user_id=user_id)
        if user.exists():
            user = user.first()

            if verify_a_user(user.user_id, req):
                # todo : 添加2FA/密码验证
                # passed all security check, update user
                if req.method == "PUT":

                    body = json.loads(req.body.decode("utf-8"))

                    user_name = require(body, "user_name", is_essential=False)
                    password = require(body, "password", is_essential=False)
                    user_email = require(body, "user_email", is_essential=False)
                    avatar = require(body, "avatar", is_essential=False)

                    # update
                    if user_name is not None:
                        if len(user_name) == 0 or len(user_name) > 50:
                            return BAD_REQUEST("Username length error")
                        if User.objects.filter(user_name=user_name).exists():
                            return CONFLICT("Username conflict")
                        user.user_name = user_name

                    if password is not None:
                        if len(password) == 0 or len(password) > 50:
                            return BAD_REQUEST("Password length error")
                        user.password = password

                    if user_email is not None:
                        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
                            return BAD_REQUEST("Invalid email address")
                        user.user_email = user_email

                    if avatar is not None:
                        user.avatar = avatar

                    user.save()
                else:
                    # passed all security check, delete user
                    user.delete()
                return request_success()
            else:
                return UNAUTHORIZED("Unauthorized")  # 401

        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD


@CheckError
def friend_management(req: HttpRequest, user_id):
    if req.method == "GET" or req.method == "PUT":
        if User.objects.filter(user_id=user_id).exists():
            if verify_a_user(user_id, req):
                # verification passed
                if req == 'GET':
                    friends = User.objects.get(user_id=user_id).get_friends()
                    return request_success({
                        "friends": [
                            return_field(friend.serialize(), ['user_id', 'user_name', 'user_email'])
                            for friend in friends
                        ]
                    })
                else:  # 'PUT'
                    body = json.loads(req.body.decode("utf-8"))

                    friend_id = require(body, 'friend_id', 'int')
                    approve = require(body, 'approve', 'bool')

                    friend = User.objects.filter(user_id=friend_id)
                    if friend.exists():
                        friend = friend.first()
                        ABFriendship = Friendship.objects.filter(user_id=user_id, friend__user_id=friend_id)
                        BAFriendship = Friendship.objects.filter(user_id=friend_id, friend__user_id=user_id)
                        if BAFriendship.exists():
                            if ABFriendship.exists():
                                if not approve:  # 删除好友
                                    ABFriendship.delete()
                                    BAFriendship.delete()
                                    # todo : 利用websocket通知好友
                                else:  # 响应好友请求
                                    if approve:  # 同意请求
                                        Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                                  friend=User.objects.get(user_id=friend_id),
                                                                  approve=True).save()
                                        # todo : 利用websocket通知好友
                                    else:  # 拒绝请求
                                        BAFriendship.delete()
                                        # todo : 利用websocket通知好友
                        else:  # 发起请求
                            Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                      friend=User.objects.get(user_id=friend_id),
                                                      approve=True).save()
                            # todo : 利用websocket通知好友
                        return request_success()
                    else:
                        return NOT_FOUND('Invalid friend id')

            else:
                return UNAUTHORIZED("Unauthorized")  # 401
        else:
            return NOT_FOUND("Invalid user id")  # 404
    else:
        return BAD_METHOD
