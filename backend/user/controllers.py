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
