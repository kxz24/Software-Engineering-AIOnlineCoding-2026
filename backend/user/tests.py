from django.test import TestCase
from rest_framework.test import APIClient

from utils.jwt import encrypt_password, verify_jwt

from .models import User

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
