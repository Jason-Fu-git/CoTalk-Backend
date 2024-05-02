from django.http import JsonResponse


def request_failed(code, info, status_code=400):
    """
    请求错误响应，默认为400 BAD REQUEST
    :param code: 错误码
    :param info: 错误信息
    :param status_code: 状态码
    :return: JsonResponse
    """
    return JsonResponse({
        "code": code,
        "info": info
    }, status=status_code)


def request_success(data={}, info='Success'):
    """
    请求成功响应
    :param data: 响应数据
    :param info: 响应信息
    :return: JsonResponse
    """
    return JsonResponse({
        "code": 0,
        "info": info,
        **data
    })


def return_field(obj_dict, field_list):
    """
    返回指定字段
    :param obj_dict: 对象字典
    :param field_list: 字段列表
    :return: 指定字段的对象字典
    """
    for field in field_list:
        assert field in obj_dict, f"Field `{field}` not found in object."

    return {
        k: v for k, v in obj_dict.items()
        if k in field_list
    }


def BAD_REQUEST(info):
    """
    各种400情况
    :param info: 错误信息
    :return: JsonResponse
    """
    return request_failed(-7, info, 400)


def NOT_FOUND(info):
    """
    各种404情况
    :param info: 错误信息
    :return: JsonResponse
    """
    return request_failed(-1, info, 404)


def UNAUTHORIZED(info):
    """
    各种未授权情况
    :param info: 错误信息
    :return: JsonResponse
    """
    return request_failed(-2, info, 401)


def CONFLICT(info):
    """
    各种冲突情况
    :param info: 错误信息
    :return: JsonResponse
    """
    return request_failed(-5, info, 409)


def PRECONDITION_FAILED(info):
    """
    各种预条件未满足情况
    :param info: 错误信息
    :return: JsonResponse
    """
    return request_failed(-6, info, 412)


def SERVER_ERROR(info):
    return request_failed(-4, info, 500)


BAD_METHOD = request_failed(-3, "Bad method", 405)
