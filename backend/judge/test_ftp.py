import io
from unittest.mock import patch
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from exam.models import ExamProblem, Submission
from exam.tests import ExamBaseTestCase
from judge.sandbox import SandboxResult
from judge.tasks import judge_submission
from problem.models import Problem


def project_zip(files):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@override_settings(JUDGE_ENQUEUE_ENABLED=False)
class CourseProjectTests(ExamBaseTestCase):
    def setUp(self):
        super().setUp()
        self.problem2.judge_profile = Problem.JUDGE_FTP
        self.problem2.save(update_fields=["judge_profile"])
        self.auth()
        self.exam_id = self.create_exam()["id"]
        self.assemble(self.exam_id)
        ExamProblem.objects.filter(exam_id=self.exam_id, problem=self.problem2).update(score=100)
        self.url = f"/api/v1/my/exams/{self.exam_id}/problems/{self.problem2.id}/submissions"
        self.archive = project_zip({
            "student/server/Makefile": "all:\n\t@true\n",
            "student/client/client": "#!/usr/bin/env python3\n",
            "student/report.pdf": "report",
        })
        self.auth(self.student_token)

    def upload(self, data):
        return self.client.post(
            self.url, {"archive": SimpleUploadedFile("project.zip", data, content_type="application/zip")},
            format="multipart",
        )

    def test_invalid_upload_does_not_consume_attempt(self):
        self.assertEqual(self.client.post(self.url, {"code": "text"}, format="json").status_code, 400)
        self.assertEqual(self.upload(project_zip({"../outside": "invalid", "server/Makefile": ""})).status_code, 400)
        self.assertFalse(Submission.objects.filter(exam_id=self.exam_id).exists())

    @patch("judge.ftp.run_ftp_sandbox")
    def test_upload_judging_and_teacher_review(self, sandbox):
        response = self.upload(self.archive)
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["used"], 1)
        submission = Submission.objects.get(pk=response.json()["submission"]["id"])
        self.assertEqual(bytes(submission.project.archive), self.archive)
        self.assertEqual(submission.code, "")
        detail_url = f"/api/v1/submissions/{submission.id}"
        review_url = detail_url + "/project-review"
        archive_url = detail_url + "/archive"
        self.assertEqual(self.client.get(archive_url).status_code, 403)
        self.assertEqual(self.client.patch(review_url, {}, format="json").status_code, 403)

        sandbox.return_value = SandboxResult(compile_output="", cases=[
            {
                "index": index, "name": f"验收项 {index}", "points": 4 if index <= 16 else 3,
                "verdict": "accepted" if index != 18 else "wrong_answer",
                "time_ms": 20, "error_excerpt": "" if index != 18 else "文件内容不一致",
            }
            for index in range(1, 19)
        ])
        judge_submission.run(submission.id)
        sandbox.assert_called_once()
        self.assertEqual(set(sandbox.call_args.args[0]), {"server/Makefile", "client/client"})
        detail = self.client.get(detail_url).json()
        self.assertEqual(detail["score"], 67)
        self.assertTrue(detail["needsReview"])
        self.assertEqual(detail["cases"][-1]["errorExcerpt"], "文件内容不一致")

        self.auth()
        self.assertEqual(self.client.get(archive_url).content, self.archive)
        points = {"warmupPoints": 9, "reportPoints": 17, "bonusPoints": 5}
        self.assertEqual(self.client.patch(review_url, {**points, "reportPoints": 21}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(review_url, points, format="json").json()["score"], 98)
        detail = self.client.get(detail_url).json()
        self.assertEqual(detail["project"]["reportPoints"], 17)
        self.assertFalse(detail["needsReview"])
