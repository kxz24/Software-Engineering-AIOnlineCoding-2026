from functools import wraps

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.jwt import jwt_authentication


def role_required(*roles):
    """
    要求登录且角色匹配的装饰器。

    用法：
        @role_required(User.ROLE_ADMIN)                 # 仅管理员
        @role_required(User.ROLE_ADMIN, User.ROLE_TEACHER)  # 管理员或教师
        @role_required()                                # 任意已登录用户

    未登录返回 401，角色不符返回 403。
    与 login_required 一样，既可用于函数视图，也可用于 APIView 的方法。
    """
    allowed = {str(r) for r in roles}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if isinstance(args[0], APIView):
                request = args[1]
            else:
                request = args[0]

            jwt_authentication(request)
            user = getattr(request, "user", None)

            if not user:
                return Response(
                    {"message": "User must be authorized."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if allowed and user.role not in allowed:
                return Response(
                    {"message": "Permission denied."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator
