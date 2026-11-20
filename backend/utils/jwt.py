# -*- coding: utf-8 -*-
import base64
import datetime

import jwt
import scrypt
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from user.controllers import get_user


def generate_jwt(payload, expiry=None):
    """
    生成jwt
    :param payload: dict 载荷
    :param expiry: datetime 有效期
    :return: 生成jwt
    """
    if expiry is None:
        now = datetime.datetime.now()
        expire_hours = (
            int(settings.JWT_EXPIRE_HOURS)
            if int(settings.JWT_EXPIRE_HOURS) > 0
            else 1
        )
        expiry = now + datetime.timedelta(hours=expire_hours)
        print("now:", now)
        print("expiry:", expiry)

    _payload = {"exp": expiry}
    _payload.update(payload)

    secret = settings.JWT_SECRET

    token = jwt.encode(_payload, secret, algorithm="HS256")

    return token


def verify_jwt(token):
    """
    校验jwt
    :param token: jwt
    :return: dict: payload
    """
    secret = settings.JWT_SECRET

    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        payload = None

    return payload


def encrypt_password(password):
    salt = settings.SALT
    key = scrypt.hash(password, salt, 32768, 8, 1, 32)
    return base64.b64encode(key).decode("ascii")


def jwt_authentication(request):
    """
    根据jwt验证用户身份
    """
    request.user = None
    token = request.headers.get("Authorization")
    if token:
        payload = verify_jwt(token)
        if payload:
            user_id = payload.get("user_id")
            user, result = get_user(user_id)
            if result:
                request.user = user


def login_required(func):
    """
    用户必须登录装饰器
    使用方法：放在 method_decorators 中
    """

    # @wraps(func)
    def wrapper(*args, **kwargs):
        if isinstance(args[0], APIView):
            request = args[1]
        else:
            request = args[0]

        jwt_authentication(request)
        if not request.user:
            return Response(
                {"message": "User must be authorized."}, status=status.HTTP_401_UNAUTHORIZED
            )
        else:
            return func(*args, **kwargs)

    return wrapper


def role_required(*allowed_roles):
    """
    角色校验装饰器（RBAC）：先做登录校验，再比对当前用户角色。
    与 login_required 用法一致，可作用于函数视图或 APIView 的方法：
        @role_required(User.ROLE_ADMIN)
        def view(request): ...

    allowed_roles 为空时退化为仅登录校验；未授权角色返回 403。
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            if isinstance(args[0], APIView):
                request = args[1]
            else:
                request = args[0]

            jwt_authentication(request)
            if not request.user:
                return Response(
                    {"message": "User must be authorized."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if allowed_roles and request.user.role not in allowed_roles:
                return Response(
                    {"message": "Permission denied: role not allowed."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return func(*args, **kwargs)

        return wrapper

    return decorator
