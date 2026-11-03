import json

from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from utils.jwt import encrypt_password, generate_jwt, login_required, role_required

from .controllers import (
    create_user,
    get_user,
    get_user_with_pass,
    list_users,
    recent_audit_logs,
    record_audit,
    update_user,
)
from .models import User


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
                record_audit(user, "login", f"{user.username} 登录成功")
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


class RegisterView(APIView):
    """
    用户注册视图类

    注册成功即视为登录，返回与登录一致的 JWT 载荷。
    管理员账号不开放注册，role 仅允许 student / teacher。
    """

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "用户名（学号 / 工号），3-32 个字符",
                    },
                    "password": {
                        "type": "string",
                        "description": "密码，6-64 个字符",
                    },
                    "nickname": {"type": "string", "description": "姓名 / 昵称"},
                    "role": {
                        "type": "string",
                        "description": "角色：student / teacher，默认 student",
                    },
                },
                "required": ["username", "password", "nickname"],
            }
        },
        responses={
            201: OpenApiResponse(
                description="注册成功",
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
            400: OpenApiResponse(description="无效的参数"),
        },
        description="用户注册接口，成功后直接返回登录态",
        summary="用户注册",
    )
    def post(self, request, *args, **kwargs):
        """
        处理用户注册请求
        """
        content = request.data or {}
        username = str(content.get("username") or "").strip()
        password = str(content.get("password") or "")
        nickname = str(content.get("nickname") or "").strip()
        role = content.get("role") or User.ROLE_STUDENT

        if not username or not password or not nickname:
            return Response(
                {"message": "用户名、密码与姓名均不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 3 <= len(username) <= 32:
            return Response(
                {"message": "用户名长度需在 3-32 个字符之间"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 6 <= len(password) <= 64:
            return Response(
                {"message": "密码长度需在 6-64 个字符之间"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if role not in (User.ROLE_STUDENT, User.ROLE_TEACHER):
            return Response(
                {"message": "注册仅支持 student / teacher 角色"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, result = create_user(
            username=username,
            password=encrypt_password(password),
            nickname=nickname,
            role=role,
        )
        if not result:
            if user == "exists":
                return Response(
                    {"message": "该用户名已被注册"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"message": "注册失败，请稍后重试"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 与登录一致：注册即登录，直接下发 JWT
        record_audit(user, "register", f"{user.username} 自助注册（{user.role}）")
        jwt = generate_jwt(
            {"user_id": user.id, "nickname": user.nickname, "role": user.role}
        )
        return Response(
            {
                "jwt": jwt,
                "userId": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "role": user.role,
            },
            status=status.HTTP_201_CREATED,
        )


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


# ---------------------------------------------------------------------------
# 账号管理（管理员）与审计日志
# ---------------------------------------------------------------------------


def _user_brief(user):
    """账号信息的统一序列化格式（camelCase，与登录接口保持一致）"""
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "role": user.role,
        "created": user.created,
    }


class UserListView(APIView):
    """
    账号列表 / 创建账号（仅管理员）
    """

    @extend_schema(
        responses={
            200: OpenApiResponse(description="账号列表"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
        },
        description="账号列表，支持按角色过滤与账号 / 姓名搜索",
        summary="账号列表",
        operation_id="list_users",
    )
    @role_required(User.ROLE_ADMIN)
    def get(self, request, *args, **kwargs):
        users = list_users(
            role=request.query_params.get("role") or None,
            keyword=request.query_params.get("keyword") or None,
        )
        return Response(
            {"users": [_user_brief(user) for user in users]},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "账号（学号 / 工号）"},
                    "nickname": {"type": "string", "description": "姓名"},
                    "password": {"type": "string", "description": "初始密码，6-64 位"},
                    "role": {
                        "type": "string",
                        "description": "角色：admin / teacher / student",
                    },
                    "email": {"type": "string", "description": "邮箱（可选）"},
                },
                "required": ["username", "nickname", "password"],
            }
        },
        responses={
            201: OpenApiResponse(description="创建成功"),
            400: OpenApiResponse(description="无效的参数 / 用户名已存在"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
        },
        description="管理员创建账号（可创建任意角色，含管理员）",
        summary="创建账号",
    )
    @role_required(User.ROLE_ADMIN)
    def post(self, request, *args, **kwargs):
        content = request.data or {}
        username = str(content.get("username") or "").strip()
        nickname = str(content.get("nickname") or "").strip()
        password = str(content.get("password") or "")
        email = str(content.get("email") or "").strip()
        role = content.get("role") or User.ROLE_STUDENT

        if not username or not nickname or not password:
            return Response(
                {"message": "账号、姓名与初始密码均不能为空"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 3 <= len(username) <= 32:
            return Response(
                {"message": "账号长度需在 3-32 个字符之间"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not 6 <= len(password) <= 64:
            return Response(
                {"message": "初始密码长度需在 6-64 个字符之间"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if role not in (User.ROLE_ADMIN, User.ROLE_TEACHER, User.ROLE_STUDENT):
            return Response(
                {"message": "角色仅支持 admin / teacher / student"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, result = create_user(
            username=username,
            password=encrypt_password(password),
            nickname=nickname,
            role=role,
        )
        if not result:
            if user == "exists":
                return Response(
                    {"message": "该账号已存在"}, status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                {"message": "创建失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST
            )
        if email:
            update_user(user.id, email=email)
            user.refresh_from_db()

        record_audit(
            request.user,
            "account.create",
            f"创建账号 {username}（{role}）",
        )
        return Response(_user_brief(user), status=status.HTTP_201_CREATED)


class UserDetailView(APIView):
    """
    查看 / 编辑单个账号（仅管理员）
    """

    @extend_schema(
        responses={
            200: OpenApiResponse(description="账号信息"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
            404: OpenApiResponse(description="账号不存在"),
        },
        description="查看单个账号信息",
        summary="账号详情",
    )
    @role_required(User.ROLE_ADMIN)
    def get(self, request, *args, **kwargs):
        user, ok = get_user(kwargs.get("user_id"))
        if not ok:
            return Response({"message": "账号不存在"}, status=status.HTTP_404_NOT_FOUND)
        return Response(_user_brief(user), status=status.HTTP_200_OK)

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "nickname": {"type": "string", "description": "姓名"},
                    "role": {
                        "type": "string",
                        "description": "角色：admin / teacher / student",
                    },
                    "password": {"type": "string", "description": "重置后的密码，6-64 位"},
                    "email": {"type": "string", "description": "邮箱"},
                },
            }
        },
        responses={
            200: OpenApiResponse(description="更新成功"),
            400: OpenApiResponse(description="无效的参数"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
            404: OpenApiResponse(description="账号不存在"),
        },
        description="编辑账号：改姓名 / 角色 / 重置密码 / 邮箱；不允许修改自己的角色",
        summary="编辑账号",
    )
    @role_required(User.ROLE_ADMIN)
    def patch(self, request, *args, **kwargs):
        target, ok = get_user(kwargs.get("user_id"))
        if not ok:
            return Response({"message": "账号不存在"}, status=status.HTTP_404_NOT_FOUND)

        content = request.data or {}
        nickname = content.get("nickname")
        role = content.get("role")
        password = content.get("password")
        email = content.get("email")

        if role is not None and role not in (
            User.ROLE_ADMIN,
            User.ROLE_TEACHER,
            User.ROLE_STUDENT,
        ):
            return Response(
                {"message": "角色仅支持 admin / teacher / student"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # 防止管理员误把自己降权后无人能管理账号
        if role is not None and target.id == request.user.id and role != request.user.role:
            return Response(
                {"message": "不能修改自己的角色"}, status=status.HTTP_400_BAD_REQUEST
            )
        if password is not None and not 6 <= len(str(password)) <= 64:
            return Response(
                {"message": "密码长度需在 6-64 个字符之间"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user, ok = update_user(
            target.id,
            nickname=str(nickname).strip() if nickname is not None else None,
            role=role,
            password=encrypt_password(password) if password else None,
            email=str(email).strip() if email is not None else None,
        )
        if not ok:
            return Response(
                {"message": "更新失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST
            )

        if role is not None and role != target.role:
            record_audit(
                request.user,
                "account.role_change",
                f"{target.username} 的角色由 {target.role} 改为 {role}",
            )
        if password:
            record_audit(request.user, "account.reset_password", f"重置 {target.username} 的密码")
        record_audit(
            request.user,
            "account.update",
            f"编辑账号 {target.username}",
        )
        return Response(_user_brief(user), status=status.HTTP_200_OK)


class UserImportView(APIView):
    """
    批量导入名单（仅管理员）。

    CSV 文本：每行「账号,姓名[,角色][,邮箱]」，角色可写 student/teacher/admin
    或 学生/教师/管理员，缺省为学生；首行若为表头（含 username）自动跳过。
    初始密码 = 账号。返回逐行成功 / 失败明细。
    """

    ROLE_ALIASES = {
        "student": User.ROLE_STUDENT,
        "teacher": User.ROLE_TEACHER,
        "admin": User.ROLE_ADMIN,
        "学生": User.ROLE_STUDENT,
        "教师": User.ROLE_TEACHER,
        "管理员": User.ROLE_ADMIN,
    }

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "CSV 文本，每行：账号,姓名[,角色][,邮箱]",
                    }
                },
                "required": ["content"],
            }
        },
        responses={
            200: OpenApiResponse(description="导入结果（含逐行明细）"),
            400: OpenApiResponse(description="内容为空"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
        },
        description="批量导入学生 / 考生名单，初始密码为账号本身",
        summary="批量导入名单",
    )
    @role_required(User.ROLE_ADMIN)
    def post(self, request, *args, **kwargs):
        content = str((request.data or {}).get("content") or "")
        lines = [line.strip() for line in content.replace("\r", "\n").split("\n")]
        lines = [line for line in lines if line]

        if not lines:
            return Response({"message": "导入内容为空"}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        created = 0
        for index, line in enumerate(lines):
            line_number = index + 1
            # 首行是表头时跳过
            if index == 0 and "username" in line.lower() and "账号" not in line:
                continue
            parts = [part.strip() for part in line.split(",")]
            username = parts[0] if parts else ""
            nickname = parts[1] if len(parts) > 1 else ""
            role_text = parts[2].lower() if len(parts) > 2 else User.ROLE_STUDENT
            email = parts[3] if len(parts) > 3 else ""

            if not username or not nickname:
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": "账号或姓名为空",
                    }
                )
                continue
            if not 3 <= len(username) <= 32:
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": "账号长度需在 3-32 个字符之间",
                    }
                )
                continue
            role = self.ROLE_ALIASES.get(role_text)
            if role is None:
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": f"无法识别的角色：{parts[2]}",
                    }
                )
                continue
            if email and "@" not in email:
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": "邮箱格式不正确",
                    }
                )
                continue

            user, ok = create_user(
                username=username,
                # 初始密码即账号，学生首次登录后可要求其修改
                password=encrypt_password(username),
                nickname=nickname,
                role=role,
            )
            if ok:
                if email:
                    update_user(user.id, email=email)
                created += 1
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": True,
                        "message": "导入成功",
                    }
                )
            elif user == "exists":
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": "账号已存在",
                    }
                )
            else:
                results.append(
                    {
                        "line": line_number,
                        "username": username,
                        "ok": False,
                        "message": "创建失败",
                    }
                )

        record_audit(
            request.user,
            "account.import",
            f"批量导入名单：成功 {created} 条 / 共 {len(results)} 条",
        )
        return Response(
            {"created": created, "total": len(results), "results": results},
            status=status.HTTP_200_OK,
        )


class AuditLogView(APIView):
    """
    审计日志（仅管理员）：登录、权限变更与关键操作记录
    """

    @extend_schema(
        responses={
            200: OpenApiResponse(description="审计日志列表"),
            401: OpenApiResponse(description="未登录"),
            403: OpenApiResponse(description="无权限（需要管理员）"),
        },
        description="最近的审计日志（默认 100 条）",
        summary="审计日志",
    )
    @role_required(User.ROLE_ADMIN)
    def get(self, request, *args, **kwargs):
        logs = recent_audit_logs(limit=100)
        return Response(
            {
                "logs": [
                    {
                        "id": log.id,
                        "username": log.user.username if log.user else "-",
                        "action": log.action,
                        "detail": log.detail,
                        "created": log.created,
                    }
                    for log in logs
                ]
            },
            status=status.HTTP_200_OK,
        )
