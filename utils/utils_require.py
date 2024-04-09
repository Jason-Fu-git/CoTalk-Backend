from functools import wraps
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile, SimpleUploadedFile
from utils.utils_request import request_failed, BAD_REQUEST, SERVER_ERROR, UNAUTHORIZED
import json

# 字长限制
MAX_MESSAGE_LENGTH = 1000
MAX_NAME_LENGTH = 50
MAX_EMAIL_LENGTH = 100
MAX_DESCRIPTION_LENGTH = 100

# 字符串
NOT_FOUND_USER_ID = "Invalid user id : user not found"
NOT_FOUND_CHAT_ID = "Invalid chat id : chat not found"
NOT_FOUND_NOTIFICATION_ID = "Invalid notification id : notification not found"

UNAUTHORIZED_JWT = "Unauthorized : JWT token is missing or invalid"
NO_MANAGEMENT_PRIVILEGE = 'No management privilege'


# A decorator function for error processing
def CheckError(check_fn):
    @wraps(check_fn)
    def decorated(*args, **kwargs):
        try:
            return check_fn(*args, **kwargs)
        except Exception as e:
            # Handle exception e
            if isinstance(e, KeyError) or isinstance(e, NotImplementedError):
                return BAD_REQUEST(str(e))
            if isinstance(e, ValueError) and str(e).startswith('Unauthorized'):
                return UNAUTHORIZED(str(e))
            if isinstance(e, json.decoder.JSONDecodeError):
                return BAD_REQUEST(f"JSON decode error: {e}")
            return SERVER_ERROR(f"Server error: {e}\n")  # 500

    return decorated


def require(body, key, dtype="string", err_msg=None, is_essential=True):
    """
    从 body 中获取 key 对应的值，并检查其类型是否为 type。
    如果类型不匹配，则抛出 KeyError 异常。
    :param body: 请求体
    :param key: 键名
    :param dtype: 期望的类型
    :param err_msg: 自定义错误信息
    :param is_essential: 是否为必需字段
    :return: body[key]
    :raise: KeyError
    """
    if key not in body.keys():
        if is_essential:
            raise KeyError(err_msg if err_msg is not None
                           else f"Invalid parameters. Expected `{key}`, but not found.")
        else:
            return None

    val = body[key]

    err_msg = f"Invalid parameters. Expected `{key}` to be `{dtype}` type." \
        if err_msg is None else err_msg

    if dtype == "int":
        try:
            val = int(val)
            return val
        except Exception as e:
            raise KeyError(err_msg)

    elif dtype == "float":
        try:
            val = float(val)
            return val
        except Exception as e:
            raise KeyError(err_msg)

    elif dtype == "string":
        try:
            val = str(val)
            return val
        except Exception as e:
            raise KeyError(err_msg)

    elif dtype == "array":
        try:
            assert isinstance(val, list)
            return val
        except Exception as e:
            raise KeyError(err_msg)

    elif dtype == 'bool':
        try:
            val = str(val)
            if val == 'True' or val == 'true' or val == 'Yes' or val == 'yes':
                return True
            elif val == 'False' or val == 'false' or val == 'No' or val == 'no':
                return False
            else:
                raise KeyError(err_msg)
        except Exception as e:
            raise KeyError(err_msg)

    elif dtype == 'image':
        if isinstance(val, UploadedFile) or isinstance(val, InMemoryUploadedFile):
            if not val.name.endswith('.jpg') and not val.name.endswith('.png') and not val.name.endswith('.jpeg'):
                raise KeyError("Invalid parameters. Expected `file` to be a image file.")
            return val
        raise KeyError(err_msg)

    else:
        raise NotImplementedError(f"Type `{dtype}` not implemented.")
