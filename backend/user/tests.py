from django.test import TestCase
from rest_framework.test import APIClient

from utils.jwt import encrypt_password, verify_jwt

from .models import AuditLog, User

# Create your tests here.
# 测试代码见test文件夹，因为测试跨APP，所以放在根目录下
# 单 app 内的接口测试放在本文件，跨 app 的放根目录 test 文件夹


class BasicTestCase(TestCase):
    pass


class RegisterAPITestCase(TestCase):
    """
    POST /api/v1/register 注册接口
    """

    def setUp(self):
        self.client = APIClient()

    def test_register_student(self):
        """默认注册为学生，返回与登录一致的字段"""
        resp = self.client.post(
            "/api/v1/register",
            {"username": "2023012345", "password": "secret6", "nickname": "李同学"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["role"], "student")
        self.assertEqual(resp.json()["username"], "2023012345")
        self.assertTrue(resp.json()["jwt"])

        user = User.objects.get(username="2023012345")
        # 库里存的应是加密后的密码，而不是明文
        self.assertEqual(user.password, encrypt_password("secret6"))
        self.assertNotEqual(user.password, "secret6")

    def test_register_teacher(self):
        """显式指定教师角色"""
        resp = self.client.post(
            "/api/v1/register",
            {
                "username": "liu_teacher",
                "password": "secret6",
                "nickname": "刘老师",
                "role": "teacher",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["role"], "teacher")

    def test_register_admin_rejected(self):
        """管理员不开放注册"""
        resp = self.client.post(
            "/api/v1/register",
            {
                "username": "hacker",
                "password": "secret6",
                "nickname": "越权",
                "role": "admin",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(User.objects.filter(username="hacker").exists())

    def test_register_duplicate_username(self):
        """用户名重复时返回 400"""
        body = {
            "username": "2023012345",
            "password": "secret6",
            "nickname": "李同学",
        }
        resp = self.client.post("/api/v1/register", body, format="json")
        self.assertEqual(resp.status_code, 201)
        resp = self.client.post("/api/v1/register", body, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

    def test_register_invalid_arguments(self):
        """缺字段 / 用户名过短 / 密码过短均返回 400"""
        cases = [
            {"username": "", "password": "secret6", "nickname": "李同学"},
            {"username": "ab", "password": "secret6", "nickname": "李同学"},
            {"username": "2023012345", "password": "123", "nickname": "李同学"},
            {"username": "2023012345", "password": "secret6", "nickname": ""},
        ]
        for body in cases:
            resp = self.client.post("/api/v1/register", body, format="json")
            self.assertEqual(resp.status_code, 400)

    def test_register_then_login(self):
        """注册后可用相同凭证登录，且注册下发的 JWT 能换取用户信息"""
        reg = self.client.post(
            "/api/v1/register",
            {"username": "2023012345", "password": "secret6", "nickname": "李同学"},
            format="json",
        )
        self.assertEqual(reg.status_code, 201)

        login = self.client.patch(
            "/api/v1/login",
            {"username": "2023012345", "password": "secret6"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["role"], "student")

        user_info = self.client.get(
            "/api/v1/user", HTTP_AUTHORIZATION=reg.json()["jwt"]
        )
        self.assertEqual(user_info.status_code, 200)
        self.assertEqual(user_info.json()["username"], "2023012345")

        # 错误密码不能登录
        bad = self.client.patch(
            "/api/v1/login",
            {"username": "2023012345", "password": "wrong99"},
            format="json",
        )
        self.assertEqual(bad.status_code, 401)

    def test_register_jwt_payload(self):
        """JWT 载荷中带有用户 id 与角色"""
        reg = self.client.post(
            "/api/v1/register",
            {"username": "2023012345", "password": "secret6", "nickname": "李同学"},
            format="json",
        )
        payload = verify_jwt(reg.json()["jwt"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], reg.json()["userId"])
        self.assertEqual(payload["role"], "student")


class AccountAdminAPITestCase(TestCase):
    """
    账号管理接口（GET/POST /api/v1/users、PATCH /api/v1/users/:id、
    POST /api/v1/users/import、GET /api/v1/audit）：仅管理员可用
    """

    def setUp(self):
        self.client = APIClient()
        # 直接建管理员，避免依赖注册接口（注册不开放 admin）
        User.objects.create(
            username="admin1",
            password=encrypt_password("secret6"),
            nickname="管理员",
            role=User.ROLE_ADMIN,
        )
        create_resp = self.client.patch(
            "/api/v1/login",
            {"username": "admin1", "password": "secret6"},
            format="json",
        )
        self.admin_token = create_resp.json()["jwt"]

        # 一个普通学生，用于验证权限与被编辑
        User.objects.create(
            username="2023012345",
            password=encrypt_password("secret6"),
            nickname="李同学",
            role=User.ROLE_STUDENT,
        )

    def auth(self, token=None):
        self.client.credentials(HTTP_AUTHORIZATION=token or self.admin_token)

    def test_rbac(self):
        """未登录 401；学生 / 教师访问账号接口 403；管理员 200"""
        self.assertEqual(self.client.get("/api/v1/users").status_code, 401)

        student_token = self.client.patch(
            "/api/v1/login",
            {"username": "2023012345", "password": "secret6"},
            format="json",
        ).json()["jwt"]
        self.auth(student_token)
        self.assertEqual(self.client.get("/api/v1/users").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/users/import", {"content": "a,b"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/audit").status_code, 403)

        User.objects.create(
            username="teacher1",
            password=encrypt_password("secret6"),
            nickname="刘老师",
            role=User.ROLE_TEACHER,
        )
        teacher_token = self.client.patch(
            "/api/v1/login",
            {"username": "teacher1", "password": "secret6"},
            format="json",
        ).json()["jwt"]
        self.auth(teacher_token)
        self.assertEqual(self.client.get("/api/v1/users").status_code, 403)

        self.auth()
        self.assertEqual(self.client.get("/api/v1/users").status_code, 200)

    def test_list_filter(self):
        """列表按角色过滤、按关键字搜索"""
        self.auth()
        resp = self.client.get("/api/v1/users", {"role": "student"})
        usernames = [item["username"] for item in resp.json()["users"]]
        self.assertEqual(usernames, ["2023012345"])

        resp = self.client.get("/api/v1/users", {"keyword": "李"})
        self.assertEqual(resp.json()["users"][0]["nickname"], "李同学")

    def test_admin_create_user(self):
        """管理员可创建任意角色账号，重复账号返回 400"""
        self.auth()
        resp = self.client.post(
            "/api/v1/users",
            {
                "username": "teacher2",
                "nickname": "新老师",
                "password": "secret6",
                "role": "teacher",
                "email": "t2@tsinghua.edu.cn",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["role"], "teacher")

        # 用初始密码能登录
        login = self.client.patch(
            "/api/v1/login", {"username": "teacher2", "password": "secret6"}, format="json"
        )
        self.assertEqual(login.status_code, 200)

        # 重复创建
        resp = self.client.post(
            "/api/v1/users",
            {"username": "teacher2", "nickname": "重复", "password": "secret6"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_admin_update_user(self):
        """编辑姓名 / 角色 / 重置密码；不能修改自己的角色"""
        self.auth()
        student = User.objects.get(username="2023012345")

        resp = self.client.patch(
            f"/api/v1/users/{student.id}",
            {"nickname": "李同学（改名）", "role": "teacher", "password": "newsecret"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.nickname, "李同学（改名）")
        self.assertEqual(student.role, "teacher")

        login = self.client.patch(
            "/api/v1/login", {"username": "2023012345", "password": "newsecret"}, format="json"
        )
        self.assertEqual(login.status_code, 200)

        admin = User.objects.get(username="admin1")
        resp = self.client.patch(
            f"/api/v1/users/{admin.id}", {"role": "student"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

        self.assertEqual(
            self.client.patch("/api/v1/users/9999", {"nickname": "x"}, format="json").status_code,
            404,
        )

    def test_import_users(self):
        """批量导入：成功 / 重复 / 非法角色逐行给出明细，中文角色可用"""
        self.auth()
        csv_content = "\n".join(
            [
                "username,nickname,role",
                "2023010001,张三,student",
                "2023010002,李四,学生",
                "2023010001,重复账号,student",
                "2023010003,王五,boss",
                "ab,过短,student",
            ]
        )
        resp = self.client.post("/api/v1/users/import", {"content": csv_content}, format="json")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["created"], 2)
        self.assertEqual(body["total"], 5)

        by_user = {item["username"]: item for item in body["results"]}
        self.assertTrue(by_user["2023010002"]["ok"])  # 中文角色「学生」同样有效
        self.assertIn("角色", by_user["2023010003"]["message"])
        self.assertFalse(by_user["ab"]["ok"])

        # 同一账号出现两次：首行成功，重复行失败
        duplicates = [r for r in body["results"] if r["username"] == "2023010001"]
        self.assertEqual(len(duplicates), 2)
        self.assertTrue(duplicates[0]["ok"])
        self.assertFalse(duplicates[1]["ok"])

        # 导入的学生初始密码为账号本身
        login = self.client.patch(
            "/api/v1/login", {"username": "2023010001", "password": "2023010001"}, format="json"
        )
        self.assertEqual(login.status_code, 200)

    def test_audit_log(self):
        """登录 / 注册 / 账号操作写入审计日志，管理员可查询"""
        self.auth()
        self.client.post(
            "/api/v1/users",
            {"username": "teacher9", "nickname": "审计", "password": "secret6"},
            format="json",
        )
        student = User.objects.get(username="2023012345")
        self.client.patch(
            f"/api/v1/users/{student.id}", {"role": "student"}, format="json"
        )

        resp = self.client.get("/api/v1/audit")
        self.assertEqual(resp.status_code, 200)
        actions = [log["action"] for log in resp.json()["logs"]]
        # setUp 里的登录 + 上面两步操作至少各有一条
        self.assertIn("login", actions)
        self.assertIn("account.create", actions)
        self.assertIn("account.update", actions)

        # 审计记录真实落库
        self.assertTrue(AuditLog.objects.filter(action="account.create").exists())
