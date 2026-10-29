import json

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.jwt import encrypt_password, generate_jwt, login_required

from .controllers import get_user_with_pass


@extend_schema(
    responses={
        200: OpenApiResponse(
            description="获取用户信息成功",
            response={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "用户ID"},
                    "username": {"type": "string", "description": "用户名"},
                    "nickname": {"type": "string", "description": "用户昵称"},
                    "role": {
                        "type": "string",
                        "description": "角色：admin / teacher / student",
                    },
                    "created": {
                        "type": "string",
                        "format": "date-time",
                        "description": "用户创建时间",
                    },
                },
            },
        ),
        401: OpenApiResponse(description="未登录"),
    },
    description="获取当前登录用户信息",
    summary="获取当前用户信息",
    operation_id="get_user_info",
)
@api_view(["GET"])
@login_required
def get_user_info(request):
    """
    获取当前登录用户信息
    """
    user = request.user
    return Response(
        {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "role": user.role,
            "created": user.created,
        },
        status=status.HTTP_200_OK,
    )


class LoginView(APIView):
    """
    用户登录视图类
    """

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "用户名"},
                    "password": {"type": "string", "description": "密码"},
                },
                "required": ["username", "password"],
            }
        },
        responses={
            200: OpenApiResponse(
                description="登录成功",
                response={
                    "type": "object",
                    "properties": {
                        "jwt": {"type": "string", "description": "JWT令牌"},
                        "userId": {"type": "integer", "description": "用户ID"},
                        "username": {"type": "string", "description": "用户名"},
                        "nickname": {"type": "string", "description": "用户昵称"},
                        "role": {
                            "type": "string",
                            "description": "角色：admin / teacher / student",
                        },
                    },
                },
            ),
            401: OpenApiResponse(description="无效的凭证"),
            405: OpenApiResponse(description="方法不允许"),
            400: OpenApiResponse(description="无效的参数"),
        },
        description="用户登录接口",
        summary="用户登录",
    )
    def patch(self, request, *args, **kwargs):
        """
        处理用户登录请求
        """
        try:
            content = request.data
            username = content.get("username")
            password = content.get("password")

            user, result = get_user_with_pass(
                username=username, password=encrypt_password(password)
            )
            if result:
                # 角色写入 JWT 载荷，后续请求可直接从 token 中取权限，
                # 不必每次都查库
                jwt = generate_jwt(
                    {
                        "user_id": user.id,
                        "nickname": user.nickname,
                        "role": user.role,
                    }
                )
                return Response(
                    {
                        "jwt": jwt,
                        "userId": user.id,
                        "username": user.username,
                        "nickname": user.nickname,
                        "role": user.role,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"message": "Invalid credentials"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        except json.JSONDecodeError:
            return Response(
                {"message": "Bad arguments"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["OPTIONS"],
        request=None,
        responses={204: OpenApiResponse(description="成功的预检请求")},
        description="处理OPTIONS请求",
        summary="OPTIONS请求",
    )
    def options(self, request, *args, **kwargs):
        """
        处理OPTIONS请求，用于获取允许的HTTP方法
        """
        return HttpResponse(status=204)


@extend_schema(
    request=None,
    responses={
        200: OpenApiResponse(description="登出成功"),
        401: OpenApiResponse(description="未登录"),
    },
    description="用户登出接口",
    summary="用户登出",
)
@api_view(["PATCH"])
@login_required
def logout(request):
    """
    登出
    当前为无状态 JWT，服务端不维护会话，由前端清除 token 即可
    """
    return Response({"message": "ok"}, status=status.HTTP_200_OK)
