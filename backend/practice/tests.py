# -*- coding: utf-8 -*-
"""自由练习接口与判题任务测试。"""
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from problem.models import Problem
from user.models import User
from utils.jwt import encrypt_password

from .models import PracticeSubmission, ProblemComment
from .tasks import judge_practice_submission


class PracticeBaseTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create(
            username="2023012345", password=encrypt_password("secret6"),
            nickname="李同学", role=User.ROLE_STUDENT,
        )
        self.other = User.objects.create(
            username="2023019999", password=encrypt_password("secret6"),
            nickname="王同学", role=User.ROLE_STUDENT,
        )
        self.teacher = User.objects.create(
            username="teacher1", password=encrypt_password("secret6"),
            nickname="刘老师", role=User.ROLE_TEACHER,
        )
        self.student_token = self.login("2023012345")
        self.other_token = self.login("2023019999")
        self.teacher_token = self.login("teacher1")

        self.problem = Problem.objects.create(
            title="练习 A+B", type=Problem.TYPE_ALGORITHM,
            language=Problem.LANGUAGE_PYTHON, difficulty=Problem.DIFFICULTY_EASY,
            description="读入两个整数，输出和。", starter_code="print(1)",
            practice_enabled=True, time_limit_ms=1000,
            memory_limit_mb=128, output_limit_kb=64, created_by=self.teacher,
        )
        self.problem.samples.create(
            name="样例 1", input_data="1 2\n", expected_output="3\n", is_sample=True
        )
        self.problem.samples.create(
            name="隐藏 1", input_data="9 9\n", expected_output="18\n", is_sample=False
        )
        self.closed_problem = Problem.objects.create(
            title="未开放题", type=Problem.TYPE_ALGORITHM,
            practice_enabled=False, created_by=self.teacher,
        )
        self.engineering = Problem.objects.create(
            title="工程题", type=Problem.TYPE_ENGINEERING,
            practice_enabled=True, created_by=self.teacher,
        )

    def login(self, username):
        return self.client.patch(
            "/api/v1/login", {"username": username, "password": "secret6"},
            format="json",
        ).json()["jwt"]

    def auth(self, token=None):
        self.client.credentials(HTTP_AUTHORIZATION=token or self.student_token)


class PracticeProblemTests(PracticeBaseTestCase):
    def test_list_only_open_algorithm_problems(self):
        self.auth()
        body = self.client.get("/api/v1/practice/problems").json()
        ids = [item["id"] for item in body["problems"]]
        self.assertEqual(ids, [self.problem.id])
        self.assertEqual(body["problems"][0]["testCount"], 2)
        self.assertEqual(body["problems"][0]["sampleCount"], 1)

    def test_detail_hides_hidden_samples(self):
        self.auth()
        body = self.client.get(f"/api/v1/practice/problems/{self.problem.id}").json()
        self.assertEqual(len(body["samples"]), 1)
        self.assertEqual(body["samples"][0]["input"], "1 2\n")
        self.assertNotIn("9 9", str(body))
        self.assertEqual(body["starterCode"], "print(1)")

    def test_closed_and_engineering_problem_not_accessible(self):
        self.auth()
        self.assertEqual(
            self.client.get(f"/api/v1/practice/problems/{self.closed_problem.id}").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(f"/api/v1/practice/problems/{self.engineering.id}").status_code,
            404,
        )

    def test_requires_login(self):
        self.client.credentials()
        self.assertEqual(self.client.get("/api/v1/practice/problems").status_code, 401)


class PracticeSubmissionTests(PracticeBaseTestCase):
    def test_submit_creates_pending_and_enqueues(self):
        self.auth()
        with mock.patch("practice.tasks.enqueue") as enqueue:
            resp = self.client.post(
                f"/api/v1/practice/problems/{self.problem.id}/submissions",
                {"code": "a, b = map(int, input().split())\nprint(a + b)\n"},
                format="json",
            )
        self.assertEqual(resp.status_code, 201)
        submission_id = resp.json()["submission"]["id"]
        self.assertEqual(PracticeSubmission.objects.get(id=submission_id).status, "pending")
        enqueue.assert_called_once_with(submission_id)

    def test_submit_validation(self):
        self.auth()
        resp = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/submissions",
            {"code": "   "}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

        self.assertEqual(
            self.client.post(
                f"/api/v1/practice/problems/{self.closed_problem.id}/submissions",
                {"code": "print(1)"}, format="json",
            ).status_code,
            404,
        )

    def test_only_owner_can_read_submission(self):
        submission = PracticeSubmission.objects.create(
            problem=self.problem, student=self.student, code="print(1)",
        )
        self.auth()
        self.assertEqual(
            self.client.get(f"/api/v1/practice/submissions/{submission.id}").status_code, 200
        )
        self.auth(self.other_token)
        self.assertEqual(
            self.client.get(f"/api/v1/practice/submissions/{submission.id}").status_code, 403
        )


class PracticeJudgeTaskTests(PracticeBaseTestCase):
    def test_task_marks_result_and_hides_hidden_output(self):
        submission = PracticeSubmission.objects.create(
            problem=self.problem, student=self.student,
            code="a, b = map(int, input().split())\nprint(a + b)\n",
        )
        fake = SimpleNamespace(
            compile_output="",
            cases=[
                {"index": 1, "verdict": "accepted", "time_ms": 12,
                 "memory_kb": 100, "output_excerpt": "3\n", "error_excerpt": ""},
                {"index": 2, "verdict": "wrong_answer", "time_ms": 15,
                 "memory_kb": 110, "output_excerpt": "18\n", "error_excerpt": ""},
            ],
        )
        with mock.patch("practice.tasks.run_sandbox", return_value=fake):
            judge_practice_submission.run(submission.id)

        submission.refresh_from_db()
        self.assertEqual(submission.status, "judged")
        self.assertEqual(submission.passed_count, 1)
        self.assertEqual(submission.total_count, 2)
        self.assertEqual(submission.sample_passed, 1)
        self.assertEqual(submission.hidden_passed, 0)
        self.assertEqual(submission.verdict, "partial")
        self.assertEqual(submission.results[0]["outputExcerpt"], "3\n")
        # 隐藏用例的输入输出/错误摘要不能下发
        self.assertEqual(submission.results[1]["outputExcerpt"], "")
        self.assertEqual(submission.results[1]["errorExcerpt"], "")
        self.assertNotIn("9 9", str(submission.results))

    def test_task_failure(self):
        submission = PracticeSubmission.objects.create(
            problem=self.problem, student=self.student, code="print(1)",
        )
        with mock.patch("practice.tasks.run_sandbox", side_effect=RuntimeError("sandbox down")):
            judge_practice_submission.run(submission.id)
        submission.refresh_from_db()
        self.assertEqual(submission.status, "failed")
        self.assertEqual(submission.verdict, "system_error")
        self.assertIn("sandbox down", submission.judge_error)


class PracticeCommentTests(PracticeBaseTestCase):
    def test_comment_with_code(self):
        self.auth()
        resp = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "这题可以用前缀和吗？", "code": "print(1)", "language": "python"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        comment = resp.json()["comment"]
        self.assertEqual(comment["username"], "2023012345")
        self.assertEqual(comment["code"], "print(1)")

        body = self.client.get(f"/api/v1/practice/problems/{self.problem.id}/comments").json()
        self.assertEqual(len(body["comments"]), 1)
        self.assertEqual(body["comments"][0]["content"], "这题可以用前缀和吗？")

    def test_reply_comment_two_levels(self):
        self.auth()
        top = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "顶层讨论"}, format="json",
        ).json()["comment"]
        reply = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "回复顶层", "parentId": top["id"]}, format="json",
        ).json()["comment"]
        self.assertEqual(reply["parentId"], top["id"])

        # 回复的回复挂到顶层，保持两级
        nested = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "回复回复", "parentId": reply["id"]}, format="json",
        ).json()["comment"]
        self.assertEqual(nested["parentId"], top["id"])

        self.assertEqual(ProblemComment.objects.filter(parent_id=top["id"]).count(), 2)

    def test_reply_to_other_problem_rejected(self):
        self.auth()
        other_comment = ProblemComment.objects.create(
            problem=self.other_problem if hasattr(self, "other_problem") else self.closed_problem,
            author=self.student, content="别处",
        )
        resp = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "错误回复", "parentId": other_comment.id}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_top_comment_cascades_replies(self):
        self.auth()
        top = ProblemComment.objects.create(
            problem=self.problem, author=self.student, content="顶层"
        )
        ProblemComment.objects.create(
            problem=self.problem, author=self.other, content="回复", parent=top
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/practice/comments/{top.id}").status_code,
            200,
        )
        self.assertFalse(ProblemComment.objects.filter(id=top.id).exists())
        self.assertEqual(ProblemComment.objects.filter(parent_id=top.id).count(), 0)

    def test_comment_requires_content_or_code(self):
        self.auth()
        resp = self.client.post(
            f"/api/v1/practice/problems/{self.problem.id}/comments",
            {"content": "", "code": ""}, format="json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_delete_own_comment_only(self):
        self.auth()
        comment = ProblemComment.objects.create(
            problem=self.problem, author=self.student, content="hi"
        )
        self.auth(self.other_token)
        self.assertEqual(
            self.client.delete(f"/api/v1/practice/comments/{comment.id}").status_code, 403
        )
        self.auth(self.teacher_token)
        self.assertEqual(
            self.client.delete(f"/api/v1/practice/comments/{comment.id}").status_code, 200
        )
        self.assertFalse(ProblemComment.objects.filter(id=comment.id).exists())
