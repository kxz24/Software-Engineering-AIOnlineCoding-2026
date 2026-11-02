from django.core.exceptions import ObjectDoesNotExist

from .models import User


def get_user(user_id):
    try:
        u = User.objects.get(id=user_id)
        return u, True
    except ObjectDoesNotExist:
        return "not found", False
    except Exception as e:
        print(e)
        return "errors", False


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
