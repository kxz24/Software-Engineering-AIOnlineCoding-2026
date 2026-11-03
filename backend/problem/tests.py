from django.test import TestCase
from rest_framework.test import APIClient

from user.controllers import create_user
from user.models import User
from utils.jwt import encrypt_password

# 题库接口测试。跨 app 的流程（如组卷）后续放在根目录 test 文件夹


def auth_header(token):
    return {"HTTP_AUTHORIZATION": token}


def login_token(client, username, password):
    resp = client.patch(
        "/api/v1/login",
        {"username": username, "password": password},
        format="json",
    )
    return resp.json()["jwt"]


class ProblemRBACTestCase(TestCase):
    """
    题库接口的角色权限：仅教师 / 管理员可用，学生一律 403
    """

    def setUp(self):
        self.client = APIClient()
        create_user(
            username="admin1",
            password=encrypt_password("secret6"),
            nickname="管理员",
            role=User.ROLE_ADMIN,
        )
        create_user(
            username="teacher1",
            password=encrypt_password("secret6"),
            nickname="刘老师",
            role=User.ROLE_TEACHER,
        )
        create_user(
            username="student1",
            password=encrypt_password("secret6"),
            nickname="李同学",
            role=User.ROLE_STUDENT,
        )

    def test_student_forbidden(self):
        """学生访问题库列表 / 创建 / 详情均为 403，未登录为 401"""
        resp = self.client.get("/api/v1/problems")
        self.assertEqual(resp.status_code, 401)

        token = login_token(self.client, "student1", "secret6")
        self.client.credentials(**auth_header(token))
        self.assertEqual(self.client.get("/api/v1/problems").status_code, 403)
        self.assertEqual(
            self.client.post(
                "/api/v1/problems", {"title": "越权创建"}, format="json"
            ).status_code,
            403,
        )
        self.assertEqual(self.client.get("/api/v1/problems/1").status_code, 403)
        self.assertEqual(self.client.delete("/api/v1/problems/1").status_code, 403)

    def test_teacher_and_admin_allowed(self):
        token = login_token(self.client, "teacher1", "secret6")
        self.client.credentials(**auth_header(token))
        self.assertEqual(self.client.get("/api/v1/problems").status_code, 200)

        self.client.credentials(**auth_header(login_token(self.client, "admin1", "secret6")))
        self.assertEqual(self.client.get("/api/v1/problems").status_code, 200)


class ProblemCRUDTestCase(TestCase):
    """
    题目的创建 / 详情 / 编辑 / 删除，测试样例随题目管理
    """

    def setUp(self):
        self.client = APIClient()
        create_user(
            username="teacher1",
            password=encrypt_password("secret6"),
            nickname="刘老师",
            role=User.ROLE_TEACHER,
        )
        token = login_token(self.client, "teacher1", "secret6")
        self.client.credentials(**auth_header(token))

    def test_create_with_samples(self):
        """创建题目并携带样例 / 隐藏测试，计数正确"""
        resp = self.client.post(
            "/api/v1/problems",
            {
                "title": "修复订单排序",
                "description": "金额相同时按创建时间升序。",
                "type": "engineering",
                "language": "python",
                "difficulty": "medium",
                "starterCode": "def sort_orders(orders): pass",
                "samples": [
                    {"name": "样例 1", "input": "A,B", "expected": "A,B", "isSample": True},
                    {"name": "隐藏 1", "input": "B,A", "expected": "A,B", "isSample": False},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["sampleCount"], 1)
        self.assertEqual(body["hiddenCount"], 1)
        self.assertEqual(len(body["samples"]), 2)
        self.assertEqual(body["createdBy"], "teacher1")

    def test_create_validation(self):
        """标题为空 / 非法语言 / 用例缺名称均返回 400"""
        cases = [
            {"title": ""},
            {"title": "好题", "language": "rust"},
            {
                "title": "好题",
                "samples": [{"name": "", "input": "", "expected": ""}],
            },
        ]
        for payload in cases:
            resp = self.client.post("/api/v1/problems", payload, format="json")
            self.assertEqual(resp.status_code, 400, payload)

    def test_detail_and_patch(self):
        """详情含题面与用例；PATCH 可换字段并整体替换用例"""
        created = self.client.post(
            "/api/v1/problems",
            {"title": "两数之和", "type": "algorithm", "language": "cpp"},
            format="json",
        ).json()

        resp = self.client.get(f"/api/v1/problems/{created['id']}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "两数之和")

        resp = self.client.patch(
            f"/api/v1/problems/{created['id']}",
            {
                "title": "两数之和（修订）",
                "difficulty": "easy",
                "samples": [
                    {"name": "样例 1", "input": "2,3", "expected": "5", "isSample": True},
                    {"name": "样例 2", "input": "-1,1", "expected": "0", "isSample": True},
                    {"name": "隐藏 1", "input": "0,0", "expected": "0", "isSample": False},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["title"], "两数之和（修订）")
        self.assertEqual(body["difficulty"], "easy")
        self.assertEqual(body["sampleCount"], 2)
        self.assertEqual(body["hiddenCount"], 1)

        # PATCH 不带 samples 键时用例保持不变
        resp = self.client.patch(
            f"/api/v1/problems/{created['id']}", {"image": "gcc:13"}, format="json"
        )
        self.assertEqual(resp.json()["hiddenCount"], 1)

    def test_delete_cascades(self):
        """删除题目后用例一并删除，详情 404"""
        created = self.client.post(
            "/api/v1/problems",
            {
                "title": "待删除",
                "samples": [{"name": "样例 1", "input": "", "expected": ""}],
            },
            format="json",
        ).json()
        problem_id = created["id"]

        resp = self.client.delete(f"/api/v1/problems/{problem_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/problems/{problem_id}").status_code, 404)

    def test_list_filter(self):
        """按关键字搜索与题型过滤"""
        self.client.post(
            "/api/v1/problems", {"title": "修复排序", "type": "engineering"}, format="json"
        )
        self.client.post(
            "/api/v1/problems", {"title": "两数之和", "type": "algorithm"}, format="json"
        )

        resp = self.client.get("/api/v1/problems", {"keyword": "排序"})
        self.assertEqual(resp.json()["problems"][0]["title"], "修复排序")

        resp = self.client.get("/api/v1/problems", {"type": "algorithm"})
        titles = [item["title"] for item in resp.json()["problems"]]
        self.assertEqual(titles, ["两数之和"])
