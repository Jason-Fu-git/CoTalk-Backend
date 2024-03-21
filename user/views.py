from django.shortcuts import render
from utils.utils_require import require, CheckRequire
from django.http import HttpRequest, JsonResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED)
from utils.utils_jwt import generate_jwt_token, verify_a_user
import json
from models import User, Friendship


@CheckRequire
def register(req: HttpRequest):
    """
    用户注册视图
    """
    try:
        if req.method != "POST":
            return BAD_METHOD

        body = json.loads(req.body.decode("utf-8"))

        user_name = require(body, "user_name", "string", err_msg="Missing or error type of [user_name]")
        password = require(body, "password", "string", err_msg="Missing or error type of [password]")
        user_email = require(body, "user_email", "string", err_msg="Missing or error type of [user_email]",
                             is_essential=False)
        avatar = require(body, "avatar", "string", err_msg="Missing or error type of [avatar]",
                         is_essential=False)  # todo:头像如何传输？

        if User.objects.filter(name=user_name).exists():  # the user exists
            return CONFLICT("Username conflict")  # 409
        else:
            user = User.objects.create(name=user_name, password=password)
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
                "avatar": user.user_icon,
            })
    except Exception as e:
        raise SERVER_ERROR(f"Server error: {e}")  # 500


@CheckRequire
def login(req: HttpRequest):
    """
    用户登录视图
    """
    try:
        if req.method != "POST":
            return BAD_METHOD

        body = json.loads(req.body.decode("utf-8"))

        user_name = require(body, "user_name", "string", err_msg="Missing or error type of [user_name]")
        password = require(body, "password", "string", err_msg="Missing or error type of [password]")
        # todo : 后续添加2FA接口

        user = User.objects.filter(name=user_name)
        if user.exists():  # the user exists
            user = user.first()
            if user.password == password:  # login success
                return request_success({
                    "token": generate_jwt_token(user_id=user.user_id),
                    "user_id": user.user_id,
                    "user_name": user.user_name,
                    "user_email": user.user_email,
                    "avatar": user.user_icon,
                })
            else:
                raise UNAUTHORIZED("Wrong password")  # 401
        else:
            raise NOT_FOUND("User Not Found")  # 404

    except Exception as e:
        raise SERVER_ERROR(f"Server error: {e}")  # 500


@CheckRequire
def update_or_delete(req: HttpRequest, index):
    """
    用户更新/删除视图
    :param req: HTTP请求
    :param index: url中的{userid}
    """
    try:
        if req.method != "DELETE" or req.method != "PUT":
            return BAD_METHOD

        user = User.objects.filter(user_id=index)
        if user.exists():
            user = user.first()

            if verify_a_user(user.user_id, req):
                # todo : 添加2FA/密码验证
                # passed all security check, update user
                if req.method == "PUT":
                    user_name = require(req, "user_name", is_essential=False)
                    password = require(req, "password", is_essential=False)
                    user_email = require(req, "user_email", is_essential=False)
                    avatar = require(req, "avatar", is_essential=False)
                    # update
                    if user_name is not None:
                        if User.objects.filter(user_name=user_name).exists():
                            raise CONFLICT("Username conflict")
                        user.user_name = user_name

                    if password is not None:
                        user.password = password

                    if user_email is not None:
                        user.user_email = user_email

                    if avatar is not None:
                        user.avatar = avatar

                    user.save()
                else:
                    # passed all security check, delete user
                    user.delete()
                return request_success()
            else:
                raise UNAUTHORIZED("Unauthorized")  # 401

        else:
            raise NOT_FOUND("Invalid user id")  # 404

    except Exception as e:
        raise SERVER_ERROR(f"Server error: {e}")  # 500
