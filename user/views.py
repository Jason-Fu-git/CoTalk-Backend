from django.shortcuts import render
from utils.utils_require import require, CheckError
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED)
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
