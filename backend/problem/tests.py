from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from io import BytesIO
import json
import zipfile
from unittest import mock
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from user.controllers import create_user
from user.models import User
from utils.jwt import encrypt_password
from exam.controllers import _problem_for_student
from exam.models import Exam, ExamProblem
from exam.controllers import publish_exam
from problem.models import Problem, ProjectBundle
from problem.project_package import ProjectPackageError, parse_package
from judge.project_sandbox import _runtime_package
from judge.tasks import prepare_project_bundle

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

    def test_algorithm_requires_description_and_samples(self):
        """算法题必须能判题：题面与至少一条测试用例缺一不可"""
        base = {"title": "算法题", "type": "algorithm", "language": "cpp"}

        resp = self.client.post("/api/v1/problems", base, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("题目描述", resp.json()["message"])

        resp = self.client.post(
            "/api/v1/problems",
            {**base, "description": "求两数之和"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("测试用例", resp.json()["message"])

        resp = self.client.post(
            "/api/v1/problems",
            {
                **base,
                "description": "求两数之和",
                "samples": [
                    {"name": "样例 1", "input": "1 2", "expected": "3", "isSample": True},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_detail_and_patch(self):
        """详情含题面与用例；PATCH 可换字段并整体替换用例"""
        created = self.client.post(
            "/api/v1/problems",
            {
                "title": "两数之和",
                "type": "algorithm",
                "language": "cpp",
                "description": "给定两个整数，求它们的和。",
                "samples": [
                    {"name": "样例 1", "input": "2,3", "expected": "5", "isSample": True},
                ],
            },
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
            "/api/v1/problems",
            {
                "title": "两数之和",
                "type": "algorithm",
                "description": "求两数之和",
                "samples": [
                    {"name": "样例 1", "input": "1 2", "expected": "3", "isSample": True},
                ],
            },
            format="json",
        )

        resp = self.client.get("/api/v1/problems", {"keyword": "排序"})
        self.assertEqual(resp.json()["problems"][0]["title"], "修复排序")

        resp = self.client.get("/api/v1/problems", {"type": "algorithm"})
        titles = [item["title"] for item in resp.json()["problems"]]
        self.assertEqual(titles, ["两数之和"])


class ProjectImportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        create_user(username="teacher_import", password=encrypt_password("secret6"),
                    nickname="教师", role=User.ROLE_TEACHER)
        token = login_token(self.client, "teacher_import", "secret6")
        self.client.credentials(**auth_header(token))

    @staticmethod
    def package(public_name="src/main.c"):
        buffer = BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("project.json", json.dumps({
                "title": "Example project", "description": "Complete the project",
                "runtime": "build-tools", "graderCommand": ["python3", "private/grade.py"],
            }))
            archive.writestr(f"public/{public_name}", "int main(void) { return 0; }")
            archive.writestr("private/grade.py", "# hidden grader")
        return SimpleUploadedFile("project.zip", buffer.getvalue(), content_type="application/zip")

    def test_teacher_import_and_student_projection(self):
        response = self.client.post("/api/v1/problems/import-project", {"file": self.package()})
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["publicFiles"]["src/main.c"], "int main(void) { return 0; }")
        problem = Problem.objects.get(pk=response.json()["id"])
        student = _problem_for_student(ExamProblem(problem=problem))
        self.assertEqual(student["publicFiles"], {"src/main.c": "int main(void) { return 0; }"})
        self.assertNotIn("graderCommand", student)
        self.assertNotIn("hidden grader", json.dumps(student))

    def test_reject_path_traversal(self):
        response = self.client.post(
            "/api/v1/problems/import-project", {"file": self.package("../escape.c")}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Problem.objects.count(), 0)

    @staticmethod
    def managed_package(environment=None, dockerfile=None):
        buffer = BytesIO()
        manifest = {
            "title": "Managed project", "description": "Complete the file",
            "graderCommand": ["python3", "private/grade.py"],
            "selfCheckMinScore": 80,
        }
        if environment is not None:
            manifest["environment"] = environment
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("project.json", json.dumps(manifest))
            archive.writestr("public/src/main.c", "int main(void) { return 0; }")
            archive.writestr("private/grade.py", "# grader")
            archive.writestr("private/selfcheck/src/main.c", "int main(void) { return 1; }")
            if dockerfile is not None:
                archive.writestr("private/Dockerfile", dockerfile)
        return buffer.getvalue()

    def test_managed_package_is_queued_and_keeps_reference_private(self):
        raw = self.managed_package({"systemPackages": ["make", "gcc"]})
        with mock.patch("judge.tasks.prepare_project_bundle.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/v1/problems/import-project",
                    {"file": SimpleUploadedFile("managed.zip", raw)},
                )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["preparationStatus"], "pending")
        self.assertNotIn("return 1", json.dumps(response.json()))
        bundle = ProjectBundle.objects.get(problem_id=response.json()["id"])
        self.assertEqual(bundle.environment["systemPackages"], ["gcc", "make"])
        enqueue.assert_called_once_with(bundle.id)
        teacher = User.objects.get(username="teacher_import")
        exam = Exam.objects.create(
            title="Managed exam", created_by=teacher,
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
        )
        ExamProblem.objects.create(exam=exam, problem=bundle.problem, score=100)
        reason, ok = publish_exam(teacher, exam)
        self.assertFalse(ok)
        self.assertIn("尚未自检通过", reason)
        bundle.preparation_status = "ready"
        bundle.save(update_fields=["preparation_status"])
        _, ok = publish_exam(teacher, exam)
        self.assertTrue(ok)

    def test_reject_shell_in_package_name(self):
        raw = self.managed_package({"systemPackages": ["gcc;touch /tmp/unsafe"]})
        with self.assertRaises(ProjectPackageError):
            parse_package(raw)

    def test_dockerfile_is_advanced_mode(self):
        raw = self.managed_package(dockerfile="FROM python:3.11-slim\n")
        metadata, public = parse_package(raw)
        self.assertEqual(metadata["environment"], {"dockerfile": True})
        self.assertEqual(list(public), ["src/main.c"])
        with mock.patch("judge.tasks.prepare_project_bundle.delay") as enqueue:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/v1/problems/import-project",
                    {"file": SimpleUploadedFile("advanced.zip", raw)},
                )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["preparationStatus"], "pending")
        enqueue.assert_called_once()

    def test_reference_and_build_files_are_removed_from_runtime_package(self):
        raw = self.managed_package(dockerfile="FROM python:3.11-slim\n")
        filtered = _runtime_package(raw)
        with zipfile.ZipFile(BytesIO(filtered)) as archive:
            self.assertIn("private/grade.py", archive.namelist())
            self.assertNotIn("private/selfcheck/src/main.c", archive.namelist())
            self.assertNotIn("private/Dockerfile", archive.namelist())

    def test_other_language_label_is_accepted_for_engineering_package(self):
        raw = self.managed_package({"systemPackages": ["ruby"]})
        source = BytesIO(raw)
        output = BytesIO()
        with zipfile.ZipFile(source) as old, zipfile.ZipFile(output, "w") as new:
            for info in old.infolist():
                content = old.read(info)
                if info.filename == "project.json":
                    manifest = json.loads(content)
                    manifest["language"] = "ruby"
                    content = json.dumps(manifest).encode()
                new.writestr(info, content)
        with mock.patch("judge.tasks.prepare_project_bundle.delay"):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/v1/problems/import-project",
                    {"file": SimpleUploadedFile("ruby.zip", output.getvalue())},
                )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["language"], "ruby")

    def test_preparation_failure_is_visible_and_retryable(self):
        raw = self.managed_package({"systemPackages": ["gcc"]})
        with mock.patch("judge.tasks.prepare_project_bundle.delay"):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    "/api/v1/problems/import-project",
                    {"file": SimpleUploadedFile("managed.zip", raw)},
                )
        self.assertEqual(response.status_code, 201, response.content)
        bundle = ProjectBundle.objects.get(problem_id=response.json()["id"])
        with mock.patch("judge.project_environment.prepare_environment", side_effect=ValueError("缺少编译工具")):
            prepare_project_bundle(bundle.id)
        bundle.refresh_from_db()
        self.assertEqual(bundle.preparation_status, "failed")
        self.assertIn("缺少编译工具", bundle.preparation_message)
        with mock.patch("judge.tasks.prepare_project_bundle.delay") as enqueue:
            retry = self.client.post(f"/api/v1/problems/{bundle.problem_id}/prepare")
        self.assertEqual(retry.status_code, 200, retry.content)
        enqueue.assert_called_once_with(bundle.id)
        bundle.refresh_from_db()
        self.assertEqual(bundle.preparation_status, "pending")
        with mock.patch("judge.project_environment.prepare_environment", return_value=("image:ready", "自检通过")):
            prepare_project_bundle(bundle.id)
        bundle.refresh_from_db()
        self.assertEqual(bundle.preparation_status, "ready")
        self.assertEqual(bundle.prepared_image, "image:ready")
