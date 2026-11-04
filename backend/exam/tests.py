from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from problem.models import Problem
from user.models import User
from utils.jwt import encrypt_password

from .models import Exam, ExamProblem, Submission

# Create your tests here.
# 测试代码见test文件夹，因为测试跨APP，所以放在根目录下
# 单 app 内的接口测试放在本文件，跨 app 的放根目录 test 文件夹


def local_iso(value):
    """aware datetime → 本地时区 ISO 串（接口入参格式）"""
    return timezone.localtime(value).isoformat()


class ExamBaseTestCase(TestCase):
    """考试接口测试的公共环境：教师 / 管理员 / 两个学生 + 两道题 + 令牌"""

    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create(
            username="teacher1", password=encrypt_password("secret6"),
            nickname="刘老师", role=User.ROLE_TEACHER,
        )
        self.admin = User.objects.create(
            username="admin1", password=encrypt_password("secret6"),
            nickname="管理员", role=User.ROLE_ADMIN,
        )
        self.student = User.objects.create(
            username="2023012345", password=encrypt_password("secret6"),
            nickname="李同学", role=User.ROLE_STUDENT,
        )
        self.other_student = User.objects.create(
            username="2023019999", password=encrypt_password("secret6"),
            nickname="王同学", role=User.ROLE_STUDENT,
        )
        self.teacher_token = self.login("teacher1")
        self.student_token = self.login("2023012345")

        self.problem1 = Problem.objects.create(
            title="两数之和", type=Problem.TYPE_ALGORITHM, language=Problem.LANGUAGE_PYTHON,
            starter_code="def two_sum(): pass", created_by=self.teacher,
        )
        self.problem1.samples.create(
            name="样例 1", input_data="[2,7]\n9", expected_output="[0,1]", is_sample=True
        )
        self.problem1.samples.create(
            name="隐藏 1", input_data="[3,2]\n5", expected_output="[0,1]", is_sample=False
        )
        self.problem2 = Problem.objects.create(
            title="修复排序", starter_code="def sort_orders(): pass", created_by=self.teacher,
        )

    def login(self, username):
        resp = self.client.patch(
            "/api/v1/login", {"username": username, "password": "secret6"}, format="json"
        )
        return resp.json()["jwt"]

    def auth(self, token=None):
        self.client.credentials(HTTP_AUTHORIZATION=token or self.teacher_token)

    def create_exam(self, **overrides):
        """建一场默认进行中（开始 1 小时前，结束 1 小时后）的考试"""
        now = timezone.now()
        body = {
            "title": "软件工程 · 期中机考",
            "course": "软件工程（2026 秋）",
            "startTime": local_iso(now - timedelta(hours=1)),
            "endTime": local_iso(now + timedelta(hours=1)),
            "durationMinutes": 120,
            "submitLimit": 2,
            "aiMode": "limited",
            "notice": "开考 15 分钟后禁止入场",
        }
        body.update(overrides)
        resp = self.client.post("/api/v1/exams", body, format="json")
        assert resp.status_code == 201, resp.content
        return resp.json()

    def assemble(self, exam_id):
        """组卷并发布"""
        resp = self.client.put(
            f"/api/v1/exams/{exam_id}/problems",
            {"problems": [{"problemId": self.problem1.id, "score": 60},
                          {"problemId": self.problem2.id, "score": 40}]},
            format="json",
        )
        assert resp.status_code == 200, resp.content
        resp = self.client.post(f"/api/v1/exams/{exam_id}/publish", {}, format="json")
        assert resp.status_code == 200, resp.content
        return resp.json()


class ExamRBACTestCase(ExamBaseTestCase):
    """考试接口的权限分级"""

    def test_rbac(self):
        """未登录 401；学生访问管理端 403；教师 / 管理员 200"""
        self.assertEqual(self.client.get("/api/v1/exams").status_code, 401)

        self.auth(self.student_token)
        self.assertEqual(self.client.get("/api/v1/exams").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/exams", {"title": "x"}, format="json").status_code, 403)
        self.assertEqual(
            self.client.post("/api/v1/exams/1/publish", {}, format="json").status_code, 403
        )

        self.auth()
        self.assertEqual(self.client.get("/api/v1/exams").status_code, 200)

        self.auth(self.login("admin1"))
        self.assertEqual(self.client.get("/api/v1/exams").status_code, 200)


class ExamManageTestCase(ExamBaseTestCase):
    """创建 / 编辑 / 组卷 / 名单 / 发布流转"""

    def test_create_list_detail(self):
        """创建后为草稿；列表与详情字段完整"""
        self.auth()
        exam = self.create_exam()

        self.assertEqual(exam["status"], "draft")
        self.assertEqual(exam["problemCount"], 0)
        self.assertTrue(exam["openToAll"])  # 名单为空 = 全体学生

        resp = self.client.get("/api/v1/exams")
        titles = [item["title"] for item in resp.json()["exams"]]
        self.assertIn("软件工程 · 期中机考", titles)

        detail = self.client.get(f"/api/v1/exams/{exam['id']}").json()
        self.assertEqual(detail["notice"], "开考 15 分钟后禁止入场")
        self.assertEqual(detail["createdBy"], "teacher1")

    def test_create_validation(self):
        """缺名称 / 时间格式 / 结束早于开始均 400"""
        self.auth()
        cases = [
            {"title": ""},                                        # 无名称
            {"title": "t", "startTime": "not-a-time"},            # 时间格式
            {"title": "t", "durationMinutes": 0},                 # 时长非法
            {"title": "t", "aiMode": "free"},                     # AI 策略非法
        ]
        for body in cases:
            resp = self.client.post("/api/v1/exams", body, format="json")
            self.assertEqual(resp.status_code, 400, body)

        now = timezone.now()
        resp = self.client.post(
            "/api/v1/exams",
            {"title": "t", "startTime": local_iso(now + timedelta(hours=2)),
             "endTime": local_iso(now + timedelta(hours=1))},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("结束时间", resp.json()["message"])

    def test_update_and_delete(self):
        """草稿可改可删；已发布未开始可改；开始后冻结；归档不可改"""
        self.auth()
        now = timezone.now()

        # 草稿：可改可删
        draft = self.create_exam(title="草稿")
        resp = self.client.patch(
            f"/api/v1/exams/{draft['id']}", {"title": "草稿（改）"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["title"], "草稿（改）")
        self.assertEqual(self.client.delete(f"/api/v1/exams/{draft['id']}").status_code, 200)

        # 已发布未开始：可改不可删
        upcoming = self.create_exam(
            title="未开始", startTime=local_iso(now + timedelta(hours=1)),
            endTime=local_iso(now + timedelta(hours=2)),
        )
        self.assemble(upcoming["id"])
        resp = self.client.patch(
            f"/api/v1/exams/{upcoming['id']}", {"notice": "new"}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self.client.delete(f"/api/v1/exams/{upcoming['id']}").status_code, 400
        )

        # 进行中：配置冻结
        ongoing = self.create_exam(title="进行中")
        self.assemble(ongoing["id"])
        resp = self.client.patch(
            f"/api/v1/exams/{ongoing['id']}", {"notice": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("冻结", resp.json()["message"])

        # 进行中：组卷与名单同样冻结
        resp = self.client.put(
            f"/api/v1/exams/{ongoing['id']}/problems",
            {"problems": [{"problemId": self.problem1.id}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("冻结", resp.json()["message"])
        resp = self.client.put(
            f"/api/v1/exams/{ongoing['id']}/candidates",
            {"candidates": ["2023012345"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("冻结", resp.json()["message"])

        # 归档后：不可改
        ended = self.create_exam(
            title="已结束", startTime=local_iso(now - timedelta(hours=2)),
            endTime=local_iso(now - timedelta(hours=1)),
        )
        self.assemble(ended["id"])
        self.client.post(f"/api/v1/exams/{ended['id']}/archive", {}, format="json")
        resp = self.client.patch(
            f"/api/v1/exams/{ended['id']}", {"notice": "y"}, format="json"
        )
        self.assertEqual(resp.status_code, 400)

    def test_assemble_problems(self):
        """组卷：顺序与分值；重复 / 不存在的题目 400"""
        self.auth()
        exam = self.create_exam()

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/problems",
            {"problems": [
                {"problemId": self.problem2.id, "score": 30},
                {"problemId": self.problem1.id, "score": 70},
            ]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        problems = resp.json()["problems"]
        self.assertEqual([p["problemId"] for p in problems], [self.problem2.id, self.problem1.id])
        self.assertEqual(problems[0]["score"], 30)
        self.assertEqual(problems[1]["sampleCount"], 1)
        self.assertEqual(problems[1]["hiddenCount"], 1)

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/problems",
            {"problems": [{"problemId": self.problem1.id}, {"problemId": self.problem1.id}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("重复", resp.json()["message"])

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/problems",
            {"problems": [{"problemId": 999}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_candidates(self):
        """名单替换；非学生账号 400；空名单回到全体学生"""
        self.auth()
        exam = self.create_exam()

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/candidates",
            {"candidates": ["2023012345"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["candidates"], ["2023012345"])
        self.assertFalse(resp.json()["openToAll"])

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/candidates",
            {"candidates": ["teacher1"]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("不是学生", resp.json()["message"])

        resp = self.client.put(
            f"/api/v1/exams/{exam['id']}/candidates", {"candidates": []}, format="json"
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["openToAll"])

    def test_publish_flow(self):
        """发布校验（时间 / 题目 / 名单）与撤回冻结"""
        self.auth()
        exam = self.create_exam()
        exam_id = exam["id"]

        # 没组卷不能发布
        resp = self.client.post(f"/api/v1/exams/{exam_id}/publish", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("组卷", resp.json()["message"])

        # 没有时间不能发布
        no_time = self.create_exam(title="无时间考试", startTime="", endTime="")
        self.client.put(
            f"/api/v1/exams/{no_time['id']}/problems",
            {"problems": [{"problemId": self.problem1.id}]}, format="json",
        )
        resp = self.client.post(f"/api/v1/exams/{no_time['id']}/publish", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("时间", resp.json()["message"])

        # 完整配置（时间 + 题目）后发布成功，重复发布 400
        self.client.put(
            f"/api/v1/exams/{exam_id}/problems",
            {"problems": [{"problemId": self.problem1.id}]}, format="json",
        )
        resp = self.client.post(f"/api/v1/exams/{exam_id}/publish", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "published")
        resp = self.client.post(f"/api/v1/exams/{exam_id}/publish", {}, format="json")
        self.assertEqual(resp.status_code, 400)

        # 未开始的考试可撤回回草稿
        now = timezone.now()
        upcoming = self.create_exam(
            title="未开始", startTime=local_iso(now + timedelta(hours=1)),
            endTime=local_iso(now + timedelta(hours=2)),
        )
        self.assemble(upcoming["id"])
        resp = self.client.post(f"/api/v1/exams/{upcoming['id']}/withdraw", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "draft")

        # 已开始的考试不能撤回
        resp = self.client.post(f"/api/v1/exams/{exam_id}/withdraw", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("冻结", resp.json()["message"])

    def test_archive_flow(self):
        """未结束不能归档；结束后归档成功且学生仍可见（历史）"""
        self.auth()
        now = timezone.now()
        exam = self.create_exam(
            title="可归档", startTime=local_iso(now - timedelta(hours=2)),
            endTime=local_iso(now - timedelta(hours=1)),
        )
        self.assemble(exam["id"])

        resp = self.client.post(f"/api/v1/exams/{exam['id']}/archive", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "archived")

        ongoing = self.create_exam(title="进行中")
        self.assemble(ongoing["id"])
        resp = self.client.post(f"/api/v1/exams/{ongoing['id']}/archive", {}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("尚未结束", resp.json()["message"])

        # 归档考试学生侧仍可见，状态为 finished
        self.auth(self.student_token)
        exams = self.client.get("/api/v1/my/exams").json()["exams"]
        archived = [e for e in exams if e["id"] == exam["id"]]
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0]["studentStatus"], "finished")


class StudentExamTestCase(ExamBaseTestCase):
    """学生侧：可见性、题面（不含隐藏测试）与提交"""

    def test_visibility(self):
        """草稿不可见；名单为空全体学生可见；指定名单只有成员可见"""
        self.auth()
        draft = self.create_exam(title="草稿不可见")
        published = self.create_exam(title="全体可见")
        self.assemble(published["id"])
        limited = self.create_exam(title="名单可见")
        # 名单要在发布前设置：开考后配置冻结（见 test_update_and_delete）
        self.client.put(
            f"/api/v1/exams/{limited['id']}/candidates",
            {"candidates": ["2023019999"]}, format="json",
        )
        self.assemble(limited["id"])

        self.auth(self.student_token)
        titles = [e["title"] for e in self.client.get("/api/v1/my/exams").json()["exams"]]
        self.assertIn("全体可见", titles)
        self.assertNotIn("草稿不可见", titles)
        self.assertNotIn("名单可见", titles)  # 名单里只有 2023019999

        # 非名单学生看详情 403，名单内学生可以
        resp = self.client.get(f"/api/v1/my/exams/{limited['id']}")
        self.assertEqual(resp.status_code, 403)
        self.auth(self.login("2023019999"))
        self.assertEqual(self.client.get(f"/api/v1/my/exams/{limited['id']}").status_code, 200)

        # 学生状态：进行中
        self.auth(self.student_token)
        detail = self.client.get(f"/api/v1/my/exams/{published['id']}").json()
        self.assertEqual(detail["status"], "ongoing")

    def test_student_detail_hides_hidden_tests(self):
        """学生题面只带样例测试与初始代码，隐藏测试不下发"""
        self.auth()
        exam = self.create_exam()
        self.assemble(exam["id"])

        self.auth(self.student_token)
        detail = self.client.get(f"/api/v1/my/exams/{exam['id']}").json()
        problem = [p for p in detail["problems"] if p["problemId"] == self.problem1.id][0]
        self.assertEqual(problem["starterCode"], "def two_sum(): pass")
        self.assertEqual(len(problem["samples"]), 1)  # 只有样例，隐藏的 1 条不在
        self.assertEqual(problem["samples"][0]["name"], "样例 1")
        self.assertNotIn("hiddenCount", problem)

    def test_submission_flow(self):
        """提交计次与剩余次数；判题未接入，状态固定 pending"""
        self.auth()
        exam = self.create_exam()
        self.assemble(exam["id"])
        exam_id = exam["id"]

        self.auth(self.student_token)
        url = f"/api/v1/my/exams/{exam_id}/problems/{self.problem1.id}/submissions"

        resp = self.client.post(url, {"code": "print(1)"}, format="json")
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["used"], 1)
        self.assertEqual(body["remaining"], 1)
        self.assertEqual(body["submission"]["status"], "pending")

        # 第二次用完
        resp = self.client.post(url, {"code": "print(2)"}, format="json")
        self.assertEqual(resp.json()["remaining"], 0)
        # 第三次超限
        resp = self.client.post(url, {"code": "print(3)"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("提交次数", resp.json()["message"])

        # 空代码 400
        other_url = f"/api/v1/my/exams/{exam_id}/problems/{self.problem2.id}/submissions"
        self.assertEqual(
            self.client.post(other_url, {"code": "   "}, format="json").status_code, 400
        )

        # 不在本场考试题目的提交 404
        resp = self.client.post(
            f"/api/v1/my/exams/{exam_id}/problems/999/submissions",
            {"code": "x"}, format="json",
        )
        self.assertEqual(resp.status_code, 404)

        # 我的提交历史（含代码）
        history = self.client.get(url).json()["submissions"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["code"], "print(2)")

        # 管理端能看到全部提交
        self.auth()
        resp = self.client.get(f"/api/v1/exams/{exam_id}/submissions").json()
        self.assertEqual(resp["total"], 2)
        self.assertEqual(resp["submissions"][0]["username"], "2023012345")

    def test_submission_time_rules(self):
        """未开始 / 已结束的考试不能提交"""
        self.auth()
        now = timezone.now()
        upcoming = self.create_exam(
            title="未开始", startTime=local_iso(now + timedelta(hours=1)),
            endTime=local_iso(now + timedelta(hours=2)),
        )
        self.assemble(upcoming["id"])
        ended = self.create_exam(
            title="已结束", startTime=local_iso(now - timedelta(hours=2)),
            endTime=local_iso(now - timedelta(minutes=5)),
        )
        self.assemble(ended["id"])

        self.auth(self.student_token)
        url = f"/api/v1/my/exams/{upcoming['id']}/problems/{self.problem1.id}/submissions"
        resp = self.client.post(url, {"code": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("尚未开始", resp.json()["message"])

        url = f"/api/v1/my/exams/{ended['id']}/problems/{self.problem1.id}/submissions"
        resp = self.client.post(url, {"code": "x"}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("已结束", resp.json()["message"])

    def test_teacher_cannot_submit_as_student(self):
        """名单为空的考试，非学生角色也不算考生"""
        self.auth()
        exam = self.create_exam()
        self.assemble(exam["id"])

        url = f"/api/v1/my/exams/{exam['id']}/problems/{self.problem1.id}/submissions"
        resp = self.client.post(url, {"code": "x"}, format="json")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("名单", resp.json()["message"])


class ExamModelTestCase(ExamBaseTestCase):
    """模型层：级联删除与唯一约束"""

    def test_delete_cascades(self):
        """删考试连带组卷 / 名单 / 提交；删题目前先移出考试"""
        self.auth()
        exam = self.create_exam()
        exam_id = exam["id"]
        self.assemble(exam_id)
        self.auth(self.student_token)
        self.client.post(
            f"/api/v1/my/exams/{exam_id}/problems/{self.problem1.id}/submissions",
            {"code": "x"}, format="json",
        )

        self.assertEqual(Submission.objects.filter(exam_id=exam_id).count(), 1)
        Exam.objects.filter(id=exam_id).delete()
        self.assertEqual(Submission.objects.filter(exam_id=exam_id).count(), 0)
        self.assertEqual(ExamProblem.objects.filter(exam_id=exam_id).count(), 0)

    def test_unique_constraints(self):
        exam = Exam.objects.create(title="约束", created_by=self.teacher)
        ExamProblem.objects.create(exam=exam, problem=self.problem1, order=0, score=50)
        with self.assertRaises(Exception):
            ExamProblem.objects.create(exam=exam, problem=self.problem1, order=1, score=50)
