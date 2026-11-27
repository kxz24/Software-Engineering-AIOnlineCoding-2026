from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from .models import AuditLog, User


def get_user(user_id):
    try:
        u = User.objects.get(id=user_id)
        return u, True
    except ObjectDoesNotExist:
        return "not found", False
    except Exception as e:
        print(e)
        return "errors", False


def list_users(role=None, keyword=None):
    """
    账号列表：可按角色过滤、按账号 / 姓名模糊搜索，按创建时间倒序
    """
    query = User.objects.all()
    if role:
        query = query.filter(role=role)
    if keyword:
        query = query.filter(
            Q(username__icontains=keyword) | Q(nickname__icontains=keyword)
        )
    return query.order_by("-created")


def update_user(user_id, nickname=None, role=None, password=None, email=None):
    """
    编辑账号（管理员）：姓名 / 角色 / 密码 / 邮箱。
    密码需为 encrypt_password 之后的密文。
    :return: (User, True) 成功；(原因字符串, False) 失败
    """
    user, ok = get_user(user_id)
    if not ok:
        return user, False
    try:
        if nickname is not None:
            user.nickname = nickname
        if role is not None:
            user.role = role
        if password is not None:
            user.password = password
        if email is not None:
            user.email = email
        user.save()
        return user, True
    except Exception as e:
        print(e)
        return "errors", False


def record_audit(user, action, detail=""):
    """
    写入一条审计日志。审计失败不应影响业务主流程，异常吞掉即可。
    """
    try:
        AuditLog.objects.create(
            user=user if user and user.id else None,
            action=action,
            detail=detail,
        )
        return True
    except Exception as e:
        print(e)
        return False


def recent_audit_logs(limit=100):
    return AuditLog.objects.select_related("user").order_by("-created")[:limit]


def get_user_by_username(username):
    """
    按用户名查用户，用于注册时校验重名
    """
    try:
        u = User.objects.get(username=username)
        return u, True
    except ObjectDoesNotExist:
        return "not found", False
    except Exception as e:
        print(e)
        return "errors", False


def create_user(username, password, nickname, role=User.ROLE_STUDENT):
    """
    创建用户。密码需为 encrypt_password 之后的密文。
    :return: (User, True) 创建成功；(原因字符串, False) 创建失败
    """
    try:
        _, exists = get_user_by_username(username)
        if exists:
            return "exists", False
        # created / updated 由 auto_now_add / auto_now 维护
        u = User.objects.create(
            username=username,
            password=password,
            nickname=nickname,
            role=role,
        )
        return u, True
    except Exception as e:
        print(e)
        return "errors", False


def get_user_with_pass(username, password):
    try:
        u = User.objects.get(username=username)
        if not u.password == password:
            return "not found", False
        return u, True
    except ObjectDoesNotExist:
        return "not found", False
    except Exception as e:
        print(e)
        return "errors", False


# ---------------------------------------------------------------------------
# 个人中心（登录用户自助）
# ---------------------------------------------------------------------------
def user_audit_logs(user, limit=20):
    """当前用户自己的最近操作记录。"""
    return (
        AuditLog.objects.filter(user=user)
        .order_by("-created", "-id")[: max(1, min(limit, 100))]
    )


def profile_stats(user):
    """按角色给出个人中心里的账号使用概况。"""
    from agent.models import AgentSession
    from exam.models import Exam, Submission
    from practice.models import PracticeSubmission
    from problem.models import Problem

    if user.role == User.ROLE_STUDENT:
        return {
            "examSubmissions": Submission.objects.filter(student=user).count(),
            "practiceSubmissions": PracticeSubmission.objects.filter(student=user).count(),
            "aiSessions": AgentSession.objects.filter(student=user).count(),
        }
    if user.role == User.ROLE_TEACHER:
        return {
            "createdExams": Exam.objects.filter(created_by=user).count(),
            "publishedExams": Exam.objects.filter(
                created_by=user, status=Exam.STATUS_PUBLISHED
            ).count(),
            "createdProblems": Problem.objects.filter(created_by=user).count(),
        }
    return {
        "users": User.objects.count(),
        "auditLogs": AuditLog.objects.count(),
    }


def profile_payload(user):
    stats = profile_stats(user)
    audits = [
        {
            "action": item.action,
            "detail": item.detail,
            "created": item.created.isoformat() if item.created else None,
        }
        for item in user_audit_logs(user)
    ]
    return {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "role": user.role,
        "status": "active",
        "created": user.created.isoformat() if user.created else None,
        "updated": user.updated.isoformat() if user.updated else None,
        "stats": stats,
        "audits": audits,
    }


def update_self(user, nickname=None, email=None):
    """本人修改姓名 / 邮箱；不做角色与密码变更（密码走独立接口）。"""
    if nickname is not None:
        nickname = str(nickname).strip()
        if not nickname or len(nickname) > 255:
            return "姓名不能为空且不超过 255 个字符", False
        user.nickname = nickname
    if email is not None:
        email = str(email).strip()
        if len(email) > 255:
            return "邮箱过长", False
        if email and ("@" not in email or "." not in email.split("@")[-1]):
            return "邮箱格式不正确", False
        user.email = email
    user.save(update_fields=["nickname", "email", "updated"])
    return user, True


def change_password(user, old_password, new_password):
    """校验原密码后修改密码；密码散列依赖 utils.jwt，延迟导入避免循环依赖。"""
    from utils.jwt import encrypt_password

    if not 6 <= len(str(new_password)) <= 64:
        return "新密码长度需在 6-64 个字符之间", False
    matched = User.objects.filter(
        id=user.id, password=encrypt_password(str(old_password))
    ).first()
    if matched is None:
        return "原密码不正确", False
    user.password = encrypt_password(str(new_password))
    user.save(update_fields=["password", "updated"])
    return user, True
