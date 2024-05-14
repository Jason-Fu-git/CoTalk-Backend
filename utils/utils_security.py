import datetime
import hashlib
import hmac
import time
import json
import base64
import random
import secrets
from typing import Optional
from django.http import HttpRequest

# c.f. https://thuse-course.github.io/course-index/basic/jwt/#jwt
# !Important! Change this to your own salt, better randomly generated!"

EXPIRE_IN_SECONDS = 60 * 60 * 24 * 1  # 1 day
ALT_CHARS = "-_".encode("utf-8")


def generate_code(length):
    code = ""
    for i in range(length):
        code += secrets.choice("0123456789")
    return code


def generate_salt():
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M")
    random_string = secrets.token_urlsafe(32)
    signature = timestamp + random_string
    return hashlib.sha256(signature.encode('utf-8')).digest()


def b64url_encode(s):
    if isinstance(s, str):
        return base64.b64encode(s.encode("utf-8"), altchars=ALT_CHARS).decode("utf-8")
    else:
        return base64.b64encode(s, altchars=ALT_CHARS).decode("utf-8")


def b64url_decode(s: str, decode_to_str=True):
    if decode_to_str:
        return base64.b64decode(s, altchars=ALT_CHARS).decode("utf-8")
    else:
        return base64.b64decode(s, altchars=ALT_CHARS)


def generate_jwt_token(salt, user_id):
    # * header
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    # dump to str. remove `\n` and space after `:`
    header_str = json.dumps(header, separators=(",", ":"))
    # use base64url to encode, instead of base64
    header_b64 = b64url_encode(header_str)

    # * payload
    payload = {
        "iat": int(time.time()),
        "exp": int(time.time()) + EXPIRE_IN_SECONDS,
        "data": {
            "user_id": user_id
        }
    }
    payload_str = json.dumps(payload, separators=(",", ":"))
    payload_b64 = b64url_encode(payload_str)

    # * signature
    signature_raw = header_b64 + "." + payload_b64
    signature = hmac.new(salt, signature_raw.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64 = b64url_encode(signature)

    return header_b64 + "." + payload_b64 + "." + signature_b64


def check_jwt_token(salt, token: str) -> Optional[dict]:
    # * Split token
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except Exception as e:
        print(str(e))
        return None

    payload_str = b64url_decode(payload_b64)

    # * Check signature
    signature_str_check = header_b64 + "." + payload_b64
    signature_check = hmac.new(salt, signature_str_check.encode("utf-8"), digestmod=hashlib.sha256).digest()
    signature_b64_check = b64url_encode(signature_check)

    if signature_b64_check != signature_b64:
        return None

    # Check expire
    payload = json.loads(payload_str)
    if payload["exp"] < time.time():
        return None

    return payload["data"]


def verify_a_user(salt, user_id, req, token=None):
    """
    Verify a user by checking the JWT token.
    :param salt : 盐
    :param user_id: The user ID to verify.
    :param req: The HTTP request.
    :param token: The JWT token to verify. If not provided, it will be retrieved from the request headers.
    """
    # check jwt token
    if token is None:
        jwt_token = req.headers.get("Authorization")
        if jwt_token is None:
            raise KeyError("Missing Authorization header")
    else:
        jwt_token = token

    # get jwt data
    jwt_data = check_jwt_token(salt, jwt_token)

    if jwt_data is None:
        raise ValueError("Unauthorized : Expired or wrong-formatted JWT token")

    if int(jwt_data["user_id"]) != int(user_id):
        print(f"User ID mismatch, expected {user_id}, got {jwt_data['user_id']}")
        raise ValueError("Unauthorized : User ID mismatch, Unauthorized")
