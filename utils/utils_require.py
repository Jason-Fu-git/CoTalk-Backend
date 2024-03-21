from functools import wraps

from utils.utils_request import request_failed

# 字长限制
MAX_MESSAGE_LENGTH = 1000
MAX_NAME_LENGTH = 50
MAX_EMAIL_LENGTH = 100


# A decorator function for processing `require` in view function.
def CheckRequire(check_fn):
    @wraps(check_fn)
    def decorated(*args, **kwargs):
        try:
            return check_fn(*args, **kwargs)
        except Exception as e:
            # Handle exception e
            error_code = -7 if len(e.args) < 2 else e.args[1]  # Bad request 默认为 -7
            return request_failed(error_code, e.args[0], 400)  # Refer to below

    return decorated


def require(body, key, dtype="string", err_msg=None, err_code=-7, is_essential=True):
    """
    从 body 中获取 key 对应的值，并检查其类型是否为 type。
    如果类型不匹配，则抛出 KeyError 异常。
    :param body: 请求体
    :param key: 键名
    :param dtype: 期望的类型
    :param err_msg: 自定义错误信息
    :param err_code: 自定义错误码
    :param is_essential: 是否为必需字段
    :return: body[key]
    :raise: KeyError
    """
    if key not in body.keys():
        if is_essential:
            raise KeyError(err_msg if err_msg is not None
                           else f"Invalid parameters. Expected `{key}`, but not found.", err_code)
        else:
            return None

    val = body[key]

    err_msg = f"Invalid parameters. Expected `{key}` to be `{dtype}` type." \
        if err_msg is None else err_msg

    if dtype == "int":
        try:
            val = int(val)
            return val
        except:
            raise KeyError(err_msg, err_code)

    elif dtype == "float":
        try:
            val = float(val)
            return val
        except:
            raise KeyError(err_msg, err_code)

    elif dtype == "string":
        try:
            val = str(val)
            return val
        except:
            raise KeyError(err_msg, err_code)

    elif dtype == "array":
        try:
            assert isinstance(val, list)
            return val
        except:
            raise KeyError(err_msg, err_code)

    else:
        raise NotImplementedError(f"Type `{dtype}` not implemented.", err_code)
