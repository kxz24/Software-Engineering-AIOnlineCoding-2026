# -*- coding: utf-8 -*-
"""判题纯函数、任务状态机与结果接口测试。"""

import io
import json
import os
import tarfile
from datetime import timedelta
from unittest import mock, skipUnless

from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from exam.models import Exam, ExamProblem, Submission, SubmissionCase
from judge.compare import normalize_output, outputs_match
from judge.constants import (
    VERDICT_ACCEPTED,
    VERDICT_COMPILE_ERROR,
    VERDICT_PARTIAL,
    VERDICT_SYSTEM_ERROR,
    VERDICT_WRONG_ANSWER,
)
from judge.languages import LANGUAGES, normalize_language, run_command
from judge.sandbox import CaseSpec, SandboxResult, _build_tar
from judge.scoring import summarize
from judge.tasks import judge_submission
from problem.models import Problem, ProjectBundle, TestSample
from user.models import User
from utils.jwt import encrypt_password


class CompareTests(SimpleTestCase):
    def test_normalize_ignores_trailing_whitespace_and_blank_lines(self):
        self.assertEqual(normalize_output("1 2  \r\n3\r\n\r\n"), "1 2\n3")

    def test_outputs_match(self):
        self.assertTrue(outputs_match("3\n", "3"))
        self.assertTrue(outputs_match("a \nb", "a\nb\n"))
        self.assertFalse(outputs_match("3", "4"))
        self.assertFalse(outputs_match("a b", "ab"))


class ScoringTests(SimpleTestCase):
    def test_all_accepted(self):
        result = summarize([
            {"verdict": VERDICT_ACCEPTED, "is_sample": True, "time_ms": 10, "memory_kb": 100},
            {"verdict": VERDICT_ACCEPTED, "is_sample": False, "time_ms": 20, "memory_kb": 200},
        ], 100)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertEqual(result["score"], 100)
        self.assertEqual((result["sample_passed"], result["sample_total"]), (1, 1))
        self.assertEqual((result["hidden_passed"], result["hidden_total"]), (1, 1))
        self.assertEqual(result["time_ms"], 20)
        self.assertFalse(result["needs_review"])

    def test_partial_credit(self):
        result = summarize([
            {"verdict": VERDICT_ACCEPTED, "is_sample": True},
            {"verdict": VERDICT_WRONG_ANSWER, "is_sample": False},
        ], 100)
        self.assertEqual(result["verdict"], VERDICT_PARTIAL)
        self.assertEqual(result["score"], 50)
        self.assertEqual(result["passed_count"], 1)

    def test_compile_error_priority(self):
        result = summarize([
            {"verdict": "compile_error", "is_sample": True},
            {"verdict": "wrong_answer", "is_sample": False},
        ], 100)
        self.assertEqual(result["verdict"], VERDICT_COMPILE_ERROR)
        self.assertEqual(result["score"], 0)

    def test_no_cases_requires_review(self):
        result = summarize([], 100)
        self.assertEqual(result["verdict"], VERDICT_SYSTEM_ERROR)
        self.assertTrue(result["needs_review"])


class LanguageTests(SimpleTestCase):
    def test_normalize_falls_back_to_problem_language(self):
        self.assertEqual(normalize_language("golang", "cpp"), "cpp")
        self.assertEqual(normalize_language("JAVA", "python"), "java")
        self.assertIsNone(normalize_language("", ""))

    def test_java_run_command_uses_memory(self):
        self.assertEqual(
            run_command(LANGUAGES["java"], 256),
            ["java", "-Xmx256m", "-cp", ".", "Main"],
        )


class TarTests(SimpleTestCase):
    def test_build_tar_contains_code_cases_and_runner(self):
        cases = [
            CaseSpec(1, "样例 1", "1 2\n", "3\n", True),
            CaseSpec(2, "隐藏", "4 5\n", "9\n", False),
        ]
        archive = _build_tar("python", "print(3)", cases, 2000, 256, 1024)
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r") as tar:
            names = set(tar.getnames())
            manifest = json.loads(tar.extractfile("manifest.json").read())
        self.assertIn("main.py", names)
        self.assertIn("runner.py", names)
        self.assertIn("cases/1.in", names)
        self.assertIn("cases/2.out", names)
        self.assertEqual(len(manifest["cases"]), 2)
        self.assertEqual(manifest["time_limit_ms"], 2000)


class JudgeTaskTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create(
            username="t1", nickname="教师", role=User.ROLE_TEACHER,
            password=encrypt_password("secret6"),
        )
        self.student = User.objects.create(
            username="s1", nickname="学生", role=User.ROLE_STUDENT,
            password=encrypt_password("secret6"),
        )
        self.other = User.objects.create(
            username="s2", nickname="另一学生", role=User.ROLE_STUDENT,
            password=encrypt_password("secret6"),
        )
        self.problem = Problem.objects.create(
            title="两数之和", type=Problem.TYPE_ALGORITHM,
            language=Problem.LANGUAGE_PYTHON, created_by=self.teacher,
        )
        self.sample = TestSample.objects.create(
            problem=self.problem, name="样例 1", input_data="1 2\n",
            expected_output="3\n", is_sample=True,
        )
        self.hidden = TestSample.objects.create(
            problem=self.problem, name="隐藏边界", input_data="4 5\n",
            expected_output="9\n", is_sample=False,
        )
        now = timezone.now()
        self.exam = Exam.objects.create(
            title="期中考试", status=Exam.STATUS_PUBLISHED,
            start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1),
            submit_limit=5, created_by=self.teacher,
        )
        ExamProblem.objects.create(
            exam=self.exam, problem=self.problem, order=0, score=100
        )
        self.submission = Submission.objects.create(
            exam=self.exam, problem=self.problem, student=self.student,
            code="print(3)", language="python",
        )

    def _result(self, sample_verdict, hidden_verdict):
        return SandboxResult(
            compile_output="",
            cases=[
                {"index": 1, "verdict": sample_verdict, "time_ms": 12,
                 "memory_kb": 1024, "output_excerpt": "3", "error_excerpt": ""},
                {"index": 2, "verdict": hidden_verdict, "time_ms": 18,
                 "memory_kb": 2048, "output_excerpt": "9", "error_excerpt": ""},
            ],
        )

    def test_task_writes_accepted_result(self):
        with mock.patch("judge.tasks.run_sandbox", return_value=self._result(
                VERDICT_ACCEPTED, VERDICT_ACCEPTED)):
            judge_submission(self.submission.id)

        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(self.submission.verdict, VERDICT_ACCEPTED)
        self.assertEqual(self.submission.score, 100)
        self.assertEqual((self.submission.sample_passed,
                          self.submission.hidden_passed), (1, 1))
        self.assertEqual(self.submission.time_ms, 18)
        cases = list(self.submission.cases.all())
        self.assertEqual(len(cases), 2)
        self.assertEqual(cases[1].name, "隐藏用例 #2")
        self.assertEqual(cases[1].output_excerpt, "")
        self.assertIsNotNone(self.submission.judged_at)

    def test_task_partial_credit(self):
        with mock.patch("judge.tasks.run_sandbox", return_value=self._result(
                VERDICT_ACCEPTED, VERDICT_WRONG_ANSWER)):
            judge_submission(self.submission.id)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.verdict, VERDICT_PARTIAL)
        self.assertEqual(self.submission.score, 50)

    def test_project_snapshot_scoring_and_private_feedback(self):
        self.problem.type = Problem.TYPE_ENGINEERING
        self.problem.save(update_fields=["type"])
        ProjectBundle.objects.create(
            problem=self.problem, archive=b"example", public_files={"src/main.c": "starter"},
            runtime="build-tools", grader_command=["python3", "private/grade.py"], max_score=100,
        )
        self.submission.code = json.dumps({"files": {"src/main.c": "answer"}})
        self.submission.save(update_fields=["code"])
        result = {"score": 65.85, "maxScore": 100, "needsReview": True, "items": [
            {"name": "public check", "score": 5, "maxScore": 5, "visible": True},
            {"name": "secret check", "score": 0, "maxScore": 5, "visible": False},
        ]}
        with mock.patch("judge.tasks.run_project_sandbox", return_value=result) as sandbox:
            judge_submission(self.submission.id)
        self.assertEqual(sandbox.call_args.args[1], {"src/main.c": "answer"})
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.score, 66)
        self.assertEqual(self.submission.verdict, VERDICT_PARTIAL)
        self.assertTrue(self.submission.needs_review)
        self.assertEqual(list(self.submission.cases.values_list("name", flat=True)),
                         ["public check", "隐藏评分项 #2"])

    def test_task_idempotent(self):
        with mock.patch("judge.tasks.run_sandbox", return_value=self._result(
                VERDICT_ACCEPTED, VERDICT_ACCEPTED)) as sandbox:
            judge_submission(self.submission.id)
            judge_submission(self.submission.id)
        self.assertEqual(sandbox.call_count, 1)
        self.assertEqual(self.submission.cases.count(), 2)

    def test_sandbox_error_marks_needs_review(self):
        with mock.patch("judge.tasks.run_sandbox",
                        side_effect=RuntimeError("docker 不可用")):
            judge_submission(self.submission.id)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.STATUS_FAILED)
        self.assertEqual(self.submission.verdict, VERDICT_SYSTEM_ERROR)
        self.assertTrue(self.submission.needs_review)
        self.assertIn("docker", self.submission.judge_error)

    def test_missing_testcases_marks_needs_review(self):
        self.problem.samples.all().delete()
        judge_submission(self.submission.id)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, Submission.STATUS_FAILED)
        self.assertTrue(self.submission.needs_review)

    def _run_real(self, code, language="python", time_limit_ms=2000):
        self.submission.code = code
        self.submission.language = language
        self.submission.save(update_fields=["code", "language"])
        self.problem.language = language
        self.problem.time_limit_ms = time_limit_ms
        self.problem.save(update_fields=["language", "time_limit_ms"])
        judge_submission(self.submission.id)
        self.submission.refresh_from_db()
        return self.submission

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_python_accepted(self):
        submission = self._run_real(
            "a, b = map(int, input().split())\nprint(a + b)\n"
        )
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, VERDICT_ACCEPTED)
        self.assertEqual(submission.score, 100)
        self.assertEqual(submission.cases.count(), 2)

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_python_wrong_answer(self):
        submission = self._run_real("print(0)\n")
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, VERDICT_WRONG_ANSWER)
        self.assertEqual(submission.score, 0)

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_python_timeout(self):
        submission = self._run_real("while True:\n    pass\n", time_limit_ms=500)
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, "time_limit_exceeded")

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_cpp_accepted(self):
        code = (
            "#include <iostream>\n"
            "int main() { int a, b; std::cin >> a >> b; std::cout << a + b << std::endl; }\n"
        )
        submission = self._run_real(code, language="cpp")
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, VERDICT_ACCEPTED)
        self.assertEqual(submission.score, 100)

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_java_accepted(self):
        code = (
            "import java.util.*;\n"
            "public class Main {\n"
            "  public static void main(String[] args) {\n"
            "    Scanner s = new Scanner(System.in);\n"
            "    System.out.println(s.nextInt() + s.nextInt());\n"
            "  }\n"
            "}\n"
        )
        submission = self._run_real(code, language="java")
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, VERDICT_ACCEPTED)
        self.assertEqual(submission.score, 100)

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_cpp_compile_error(self):
        submission = self._run_real("int main( {", language="cpp")
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, VERDICT_COMPILE_ERROR)
        self.assertEqual(submission.score, 0)
        self.assertTrue(submission.compile_output)

    @skipUnless(os.environ.get("JUDGE_INTEGRATION") == "1",
                "需要 Docker 与 aicoding-judge 镜像（设置 JUDGE_INTEGRATION=1）")
    def test_docker_output_limit(self):
        submission = self._run_real("print('x' * 2000000)\n")
        self.assertEqual(submission.status, Submission.STATUS_JUDGED)
        self.assertEqual(submission.verdict, "output_limit_exceeded")


class SubmissionDetailApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.teacher = User.objects.create(
            username="t1", nickname="教师", role=User.ROLE_TEACHER,
            password=encrypt_password("secret6"),
        )
        self.student = User.objects.create(
            username="s1", nickname="学生", role=User.ROLE_STUDENT,
            password=encrypt_password("secret6"),
        )
        self.other = User.objects.create(
            username="s2", nickname="另一学生", role=User.ROLE_STUDENT,
            password=encrypt_password("secret6"),
        )
        self.problem = Problem.objects.create(
            title="两数之和", type=Problem.TYPE_ALGORITHM,
            language=Problem.LANGUAGE_PYTHON, created_by=self.teacher,
        )
        sample = TestSample.objects.create(
            problem=self.problem, name="样例 1", input_data="1 2",
            expected_output="3", is_sample=True,
        )
        hidden = TestSample.objects.create(
            problem=self.problem, name="隐藏边界", input_data="4 5",
            expected_output="9", is_sample=False,
        )
        now = timezone.now()
        self.exam = Exam.objects.create(
            title="期中考试", status=Exam.STATUS_PUBLISHED,
            start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1),
            submit_limit=5, created_by=self.teacher,
        )
        ExamProblem.objects.create(
            exam=self.exam, problem=self.problem, order=0, score=100
        )
        self.submission = Submission.objects.create(
            exam=self.exam, problem=self.problem, student=self.student,
            code="print(3)", language="python",
            status=Submission.STATUS_JUDGED, verdict=VERDICT_PARTIAL,
            score=50, passed_count=1, total_count=2,
            sample_passed=1, sample_total=1,
            hidden_passed=0, hidden_total=1, time_ms=20, memory_kb=2048,
        )
        SubmissionCase.objects.create(
            submission=self.submission, case_index=1, sample=sample,
            is_sample=True, name="样例 1", verdict=VERDICT_ACCEPTED,
            time_ms=10, memory_kb=1024, output_excerpt="3",
        )
        SubmissionCase.objects.create(
            submission=self.submission, case_index=2, sample=hidden,
            is_sample=False, name="隐藏用例 #2", verdict=VERDICT_WRONG_ANSWER,
            time_ms=20, memory_kb=2048,
        )

    def auth(self, username):
        resp = self.client.patch(
            "/api/v1/login", {"username": username, "password": "secret6"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=resp.json()["jwt"])

    def test_owner_can_see_result_and_cases(self):
        self.auth("s1")
        resp = self.client.get(f"/api/v1/submissions/{self.submission.id}")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["score"], 50)
        self.assertEqual(len(body["cases"]), 2)
        self.assertIn("outputExcerpt", body["cases"][0])
        # 隐藏用例不返回输出 / 错误 / 输入 / 期望
        hidden = body["cases"][1]
        self.assertFalse(hidden["isSample"])
        for key in ("outputExcerpt", "errorExcerpt", "input", "expected"):
            self.assertNotIn(key, hidden)

    def test_other_student_forbidden(self):
        self.auth("s2")
        resp = self.client.get(f"/api/v1/submissions/{self.submission.id}")
        self.assertEqual(resp.status_code, 403)

    def test_teacher_can_see_code(self):
        self.auth("t1")
        resp = self.client.get(f"/api/v1/submissions/{self.submission.id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["code"], "print(3)")


class EnqueueTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create(
            username="t1", nickname="教师", role=User.ROLE_TEACHER,
            password=encrypt_password("secret6"),
        )
        self.student = User.objects.create(
            username="s1", nickname="学生", role=User.ROLE_STUDENT,
            password=encrypt_password("secret6"),
        )
        self.problem = Problem.objects.create(
            title="两数之和", type=Problem.TYPE_ALGORITHM,
            language=Problem.LANGUAGE_PYTHON, created_by=self.teacher,
        )
        TestSample.objects.create(
            problem=self.problem, name="样例 1", input_data="1 2",
            expected_output="3", is_sample=True,
        )
        now = timezone.now()
        self.exam = Exam.objects.create(
            title="期中考试", status=Exam.STATUS_PUBLISHED,
            start_time=now - timedelta(hours=1), end_time=now + timedelta(hours=1),
            submit_limit=5, created_by=self.teacher,
        )
        ExamProblem.objects.create(
            exam=self.exam, problem=self.problem, order=0, score=100
        )

    def test_submit_enqueues_after_commit(self):
        client = APIClient()
        login = client.patch(
            "/api/v1/login", {"username": "s1", "password": "secret6"},
            format="json",
        )
        client.credentials(HTTP_AUTHORIZATION=login.json()["jwt"])
        url = (
            f"/api/v1/my/exams/{self.exam.id}"
            f"/problems/{self.problem.id}/submissions"
        )
        with mock.patch("judge.tasks.judge_submission.delay") as delay:
            with self.captureOnCommitCallbacks(execute=True):
                resp = client.post(url, {"code": "print(3)"}, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["submission"]["status"], "pending")
        delay.assert_called_once()
