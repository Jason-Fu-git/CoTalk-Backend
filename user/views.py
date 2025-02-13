from utils.utils_require import (require, CheckError, MAX_DESCRIPTION_LENGTH, MAX_EMAIL_LENGTH, MAX_NAME_LENGTH,
                                 NOT_FOUND_USER_ID, NOT_FOUND_CHAT_ID, NOT_FOUND_NOTIFICATION_ID, UNAUTHORIZED_JWT)
from django.http import HttpRequest, JsonResponse, FileResponse
from utils.utils_request import (BAD_METHOD, request_success, request_failed, BAD_REQUEST,
                                 CONFLICT, SERVER_ERROR, NOT_FOUND, UNAUTHORIZED, PRECONDITION_FAILED, return_field)
from utils.utils_security import generate_jwt_token, verify_a_user, generate_salt, generate_code
from utils.utils_time import get_timestamp
import json
import re
from .models import User, Friendship
from channels.layers import get_channel_layer
from ws.models import Client
from asgiref.sync import async_to_sync
from chat.models import Chat, Membership
from message.models import Notification, leave_chat, change_privilege
from .email_sender import send_email, generate_email_content
from django.contrib.auth.hashers import make_password, check_password


@CheckError
def register(req: HttpRequest):
    """
    用户注册视图
    """
    if req.method != "POST":
        return BAD_METHOD  # 405

    user_name = require(req.POST, "user_name", "string", err_msg="Missing or error type of [user_name]", req=req)
    password = require(req.POST, "password", "string", err_msg="Missing or error type of [password]", req=req)
    user_email = require(req.POST, "user_email", "string", err_msg="Missing or error type of [user_email]",
                         is_essential=False, req=req)
    user_phone = require(req.POST, "user_phone", "string", err_msg="Missing or error type of [user_phone]",
                         is_essential=False, req=req)
    description = require(req.POST, "description", "string", err_msg="Missing or error type of [description]",
                          is_essential=False, req=req)
    avatar = require(req.FILES, "avatar", "image", err_msg="Missing or error type of [avatar]", is_essential=False)

    # check validity of user_name , password, user_email and description
    if len(user_name) == 0 or len(user_name) > MAX_NAME_LENGTH:
        return BAD_REQUEST("Username length error")  # 400

    if len(password) == 0 or len(password) > MAX_NAME_LENGTH:
        return BAD_REQUEST("Password length error")  # 400

    if user_email is not None:
        if len(user_email) == 0 or len(user_email) > MAX_EMAIL_LENGTH:
            return BAD_REQUEST("Email length error")  # 400
        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
            return BAD_REQUEST("Invalid email address")  # 400

    if user_phone is not None:
        if len(user_phone) == 0 or len(user_phone) > MAX_EMAIL_LENGTH:
            return BAD_REQUEST("Phone length error")  # 400
        if not re.match(r"^[0123456789]+$", user_phone):
            return BAD_REQUEST("Invalid phone number")  # 400

    if description is not None:
        if len(description) > MAX_DESCRIPTION_LENGTH:
            return BAD_REQUEST("Description length error")  # 400

    # check user_name conflict
    if User.objects.filter(user_name=user_name).exists():
        return CONFLICT("Username conflict")  # 409
    else:
        # encode password
        password = make_password(password)
        user = User.objects.create(user_name=user_name, password=password, jwt_token_salt=generate_salt())
        if user_email is not None:
            user.user_email = user_email
        if user_phone is not None:
            user.user_phone = user_phone
        if avatar is not None:
            user.user_icon = avatar
        if description is not None and len(description) > 0:
            user.description = description
        user.save()

        return request_success({
            "token": generate_jwt_token(salt=user.jwt_token_salt, user_id=user.user_id),
            "user_id": user.user_id,
            "user_name": user.user_name,
            "user_email": user.user_email,
            "user_phone": user.user_phone,
            "description": user.description,
            "register_time": user.register_time,
        })


@CheckError
def login(req: HttpRequest):
    """
    用户登录视图
    """
    if req.method != "POST":
        return BAD_METHOD  # 405

    body = json.loads(req.body.decode("utf-8"))
    user_name = require(body, "user_name", "string", err_msg="Missing or error type of [user_name]")
    password = require(body, "password", "string", err_msg="Missing or error type of [password]")
    if not User.objects.filter(user_name=user_name).exists():
        return NOT_FOUND("User Not Found")  # 404

    user = User.objects.get(user_name=user_name)

    if not check_password(password, user.password):  # login failed
        return UNAUTHORIZED("Unauthorized : Wrong password")  # 401

    SALT = generate_salt()
    user.jwt_token_salt = SALT
    user.save()
    return request_success({
        "token": generate_jwt_token(salt=SALT, user_id=user.user_id),
        "user_id": user.user_id,
        "user_name": user.user_name,
        "user_email": user.user_email,
        "user_phone": user.user_phone,
        "description": user.description,
        "register_time": user.register_time,
    })


@CheckError
def get_user_avatar(req: HttpRequest, user_id):
    """
        用户头像获取视图
        :param req: HTTP请求
        :param user_id: url中的{user_id}
        """
    if req.method != 'GET':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError:
        return BAD_REQUEST("User id must be an integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND("Invalid user id")  # 404

    return FileResponse(User.objects.get(user_id=user_id).user_icon)


@CheckError
def user_management(req: HttpRequest, user_id):
    """
    用户详细信息获取/更新/删除视图
    :param req: HTTP请求
    :param user_id: url中的{user_id}
    """
    if req.method != "DELETE" and req.method != "POST" and req.method != 'GET':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError:
        return BAD_REQUEST("User id must be an integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND("Invalid user id")  # 404

    user = User.objects.get(user_id=user_id)
    SALT = user.jwt_token_salt

    if req.method == "GET":  # 获取用户信息
        return request_success(user.serialize())

    verify_a_user(salt=SALT, user_id=user.user_id, req=req)

    # passed all security check, update user
    if req.method == "POST":
        user_name = require(req.POST, "user_name", 'string', is_essential=False, req=req)
        password = require(req.POST, "password", 'string', is_essential=False, req=req)
        user_email = require(req.POST, "user_email", 'string', is_essential=False, req=req)
        user_phone = require(req.POST, "user_phone", "string", is_essential=False, req=req)
        description = require(req.POST, "description", 'string', is_essential=False, req=req)
        avatar = require(req.FILES, "avatar", 'image', is_essential=False)

        # password change needs verification code
        if password is not None:
            if len(password) == 0 or len(password) > MAX_NAME_LENGTH:
                return BAD_REQUEST("Password length error")
            # check code
            code = require(req.POST, "code", 'string', is_essential=True, req=req)
            if user.verification_code is None or len(user.verification_code) == 0:
                return BAD_REQUEST("Verification code not sent")
            if str(code) != str(user.verification_code):
                return UNAUTHORIZED("Invalid verification code")
            if get_timestamp() > user.modify_time + 60 * 15:  # 15 minutes
                return UNAUTHORIZED("Verification code expired")
            # encode
            password = make_password(password)
            # update password
            user.password = password
            user.verification_code = ""
        else:
            # other change needs password verification
            old_password = require(req.POST, "old_password", 'string', req=req)
            if not check_password(old_password, user.password):
                return UNAUTHORIZED("Invalid password")

            # update
            if user_name is not None:
                if len(user_name) > MAX_NAME_LENGTH:
                    return BAD_REQUEST("Username length error")
                if user_name != User.objects.get(user_id=user_id).user_name and User.objects.filter(
                        user_name=user_name).exists():
                    return CONFLICT("Username conflict")
                if len(user_name) > 0:
                    user.user_name = user_name
            if user_email is not None:
                if len(user_email) == 0 or len(user_email) > MAX_EMAIL_LENGTH:
                    return BAD_REQUEST("Email length error")
                if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", user_email):
                    return BAD_REQUEST("Invalid email address")
                user.user_email = user_email
            if user_phone is not None:
                if len(user_phone) == 0 or len(user_phone) > MAX_EMAIL_LENGTH:
                    return BAD_REQUEST("Phone length error")
                if not re.match(r"^[0-9]+$", user_phone):
                    return BAD_REQUEST("Invalid phone number")
                user.user_phone = user_phone
            if description is not None:
                if len(description) > MAX_DESCRIPTION_LENGTH:
                    return BAD_REQUEST("Description length error")
                if len(description) > 0:
                    user.description = description
            if avatar is not None:
                user.user_icon = avatar
        user.save()
    else:  # DELETE
        # first delete the private chats
        private_chats = Chat.objects.filter(is_private=True)
        for chat in private_chats:
            if (chat.get_memberships()[0].user.user_id == user_id
                    or chat.get_memberships()[1].user.user_id == user_id):
                chat.get_memberships().delete()
                chat.delete()
        # passed all security check, delete user
        user.delete()
    return request_success()


@CheckError
def friend_management(req: HttpRequest, user_id):
    """
    好友管理/好友列表获取视图
    """
    if req.method != "GET" and req.method != "PUT":
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError:
        return BAD_REQUEST("User id must be an integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    SALT = user.jwt_token_salt

    verify_a_user(salt=SALT, user_id=user.user_id, req=req)

    # verification passed
    if req.method == 'GET':
        friends = User.objects.get(user_id=user_id).get_friends()
        return request_success({
            "friends": [
                {**return_field(User.objects.get(user_id=friend['friend']).serialize(),
                                ['user_id', 'user_name', 'user_email', 'user_phone', 'description', 'register_time'])
                    , 'group': friend['group']}
                for friend in friends
            ]
        })
    else:  # 'PUT'
        body = json.loads(req.body.decode("utf-8"))

        friend_id = require(body, 'friend_id', 'int')
        approve = require(body, 'approve', 'bool', is_essential=False)
        group = require(body, 'group', 'string', is_essential=False)
        if approve is None:
            approve = True

        if not User.objects.filter(user_id=friend_id).exists():
            return NOT_FOUND("Invalid friend id : friend not found")

        # 尝试获取对应websocket
        if Client.objects.filter(user_id=friend_id).exists():
            channel_name = Client.objects.get(user_id=friend_id).channel_name
        else:
            channel_name = None

        # 判断是哪种情况
        abFriendship = Friendship.objects.filter(user_id=user_id, friend__user_id=friend_id)
        baFriendship = Friendship.objects.filter(user_id=friend_id, friend__user_id=user_id)

        # 通知
        notification_dict = None

        if baFriendship.exists():
            if abFriendship.exists():
                if not approve:  # 删除好友
                    abFriendship.delete()
                    baFriendship.delete()
                    notification_dict = {
                        'type': 'user.friend.request',
                        'status': 'delete',
                        'text': f'{user.user_name} 终止了与您的好友关系',
                        'user_id': user_id,
                        'is_approved': approve,
                    }
                    # 删除私聊
                    Chat.objects.filter(chat_name=f"Private {user_id}&{friend_id}", is_private=True).delete()
                    Chat.objects.filter(chat_name=f"Private {friend_id}&{user_id}", is_private=True).delete()
                elif group is not None:  # 更改分组
                    abFriendship.update(group=group)
            else:  # 响应好友请求
                if approve:  # 同意请求
                    abFriendship = Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                             friend=User.objects.get(user_id=friend_id),
                                                             is_approved=True)
                    baFriendship = baFriendship.first()
                    baFriendship.is_approved = True
                    baFriendship.save()
                    notification_dict = {
                        'type': 'user.friend.request',
                        'status': 'accept request',
                        'text': f'{user.user_name} 接受了您的好友请求',
                        'user_id': user_id,
                        'is_approved': approve,
                    }
                    # 设置分组
                    if group is not None:
                        abFriendship.group = group
                        abFriendship.save()
                    # 此时，建立私聊
                    chat = Chat.objects.create(chat_name=f"Private {user_id}&{friend_id}", is_private=True)
                    Membership.objects.create(user_id=user_id, privilege='O', chat=chat, is_approved=True)
                    Membership.objects.create(user_id=friend_id, privilege='M', chat=chat, is_approved=True)
                else:  # 拒绝请求
                    baFriendship.delete()
                    notification_dict = {
                        'type': 'user.friend.request',
                        'status': 'reject request',
                        'text': f'{user.user_name} 拒绝了您的好友请求',
                        'user_id': user_id,
                        'is_approved': approve,
                    }
        else:  # 发起请求
            abFriendship = Friendship.objects.create(user=User.objects.get(user_id=user_id),
                                                     friend=User.objects.get(user_id=friend_id),
                                                     is_approved=False)  # 首次请求的APPROVE应该是False
            notification_dict = {
                'type': 'user.friend.request',
                'status': 'make request',
                'text': f'{user.user_name} 请求添加您为好友',
                'user_id': user_id,
                'is_approved': approve,
            }
            # 设置分组
            if group is not None:
                abFriendship.group = group
                abFriendship.save()

        if notification_dict is not None:
            # 执行通知
            if channel_name is not None:  # websocket 通知
                async_to_sync(get_channel_layer().send)(
                    channel_name,
                    notification_dict
                )
            # else:
            # 静态 notification
            Notification.objects.create(
                sender_id=user_id,
                receiver_id=friend_id,
                content=str(notification_dict)
            )
        return request_success()


@CheckError
def search(req: HttpRequest):
    """
    搜索用户
    """
    if req.method == 'GET':
        search_text = require(req.GET, 'search_text', 'string', is_essential=False)
        if search_text is None or search_text == '':
            users = User.objects.all()
        else:
            users = User.objects.filter(user_name__contains=search_text) | User.objects.filter(
                user_email__contains=search_text) | User.objects.filter(
                description__contains=search_text) | User.objects.filter(
                user_phone__contains=search_text)
        return request_success({
            'users': [
                return_field(user.serialize(),
                             ['user_id', 'user_name', 'user_email', 'user_phone', 'description', 'register_time'])
                for user in users if user.user_name != 'system'
            ]
        })
    else:
        return BAD_METHOD


@CheckError
def user_chats_management(req: HttpRequest, user_id):
    """
    获取聊天列表/退出聊天
    """
    if req.method != 'GET' and req.method != 'DELETE':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError:
        return BAD_REQUEST("User id must be an integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)
    verify_a_user(salt=user.jwt_token_salt, user_id=user_id, req=req)

    # verification passed
    if req.method == 'GET':  # 获取聊天列表
        chats = user.get_chats()
        if len(chats) == 0:
            return request_success({'chats': []})
        else:
            return request_success({
                'chats': [
                    return_field(Chat.objects.get(chat_id=chat['chat']).serialize(),
                                 ['chat_id', 'chat_name', 'create_time', 'is_private'])
                    for chat in chats]
            })
    else:  # DELETE
        body = json.loads(req.body.decode('utf-8'))
        chat_id = require(body, 'chat_id', "int")
        if Membership.objects.filter(user_id=user_id, chat_id=chat_id).exists():
            membership = Membership.objects.get(user_id=user_id, chat_id=chat_id)
            if membership.chat.is_private:
                return PRECONDITION_FAILED("Cannot delete private chat")

            is_owner = membership.privilege == 'O'
            membership.delete()
            chat = Chat.objects.get(chat_id=chat_id)
            if len(chat.get_memberships()) == 0:  # no people left, delete the chat
                chat.delete()
                return request_success()
            elif is_owner:  # owner exits, handover owner privilege

                if chat.get_admins().exists():
                    new_owner = chat.get_admins().first().user
                else:
                    new_owner = chat.get_memberships().first().user

                # 更改新群主的权限
                membership_owner = Membership.objects.get(
                    user=new_owner,
                    chat_id=chat_id)
                membership_owner.privilege = 'O'
                membership_owner.save()
                # 新建系统消息
                change_privilege(admin_id=user_id, member_id=new_owner.user_id, chat_id=chat_id, privilege='owner')

            # 新建系统消息
            leave_chat(chat_id=chat_id, user_id=user_id)
            return request_success()
        else:
            return NOT_FOUND("Invalid chat id or user not in chat")


@CheckError
def get_notification_list(req: HttpRequest, user_id):
    """
    获取通知列表
    """
    if req.method != 'GET':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError as e:
        return BAD_REQUEST("Invalid user id : must be integer")  # 400

    only_unread = require(req.GET, 'only_unread', 'bool', is_essential=False)
    later_than = require(req.GET, 'later_than', 'float', is_essential=False)

    if only_unread is None:
        only_unread = False

    if later_than is None:
        later_than = 0

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)

    verify_a_user(salt=user.jwt_token_salt, req=req, user_id=user_id)

    if only_unread:
        notifications = Notification.objects.filter(receiver=user, is_read=False, create_time__gte=later_than)
    else:
        notifications = Notification.objects.filter(receiver=user, create_time__gte=later_than)

    return request_success({
        'notifications': [
            return_field(notification.serialize(), [
                'notification_id',
                'sender_id',
                'content',
                'create_time',
                'is_read',
            ])
            for notification in notifications]
    })


@CheckError
def notification_detail_or_delete_or_read(req: HttpRequest, user_id, notification_id):
    """
    获取通知详情/删除通知
    """
    if req.method != 'GET' and req.method != 'DELETE' and req.method != 'PUT':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
        notification_id = int(notification_id)
    except ValueError as e:
        return BAD_REQUEST("Invalid user id or notification id : must be integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    if not Notification.objects.filter(notification_id=notification_id).exists():
        return NOT_FOUND(NOT_FOUND_NOTIFICATION_ID)  # 404

    user = User.objects.get(user_id=user_id)
    notification = Notification.objects.get(notification_id=notification_id)

    verify_a_user(salt=user.jwt_token_salt, req=req, user_id=user_id)

    if req.method == 'GET':
        return request_success({
            "notification_id": notification.notification_id,
            "sender_id": notification.sender.user_id,
            "content": notification.content,
            "create_time": notification.create_time,
            "is_read": notification.is_read
        })
    elif req.method == 'DELETE':
        notification.delete()
    else:  # 'PUT'
        notification.is_read = True
        notification.save()
    return request_success()


def user_verification(req: HttpRequest, user_id):
    """
    向绑定邮箱发送验证码
    """
    if req.method != 'PUT':
        return BAD_METHOD  # 405

    try:
        user_id = int(user_id)
    except ValueError as e:
        return BAD_REQUEST("Invalid user id : must be integer")  # 400

    if not User.objects.filter(user_id=user_id).exists():
        return NOT_FOUND(NOT_FOUND_USER_ID)  # 404

    user = User.objects.get(user_id=user_id)

    verify_a_user(salt=user.jwt_token_salt, req=req, user_id=user_id)

    # send code
    code = generate_code(6)
    email_content = generate_email_content(user.user_email, code)
    success = send_email(user.user_email, email_content.as_string())

    if not success:
        return SERVER_ERROR("Failed to send email")

    # save code
    user.verification_code = code
    user.modify_time = get_timestamp()
    user.save()

    return request_success()
