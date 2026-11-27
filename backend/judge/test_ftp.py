import io
import json
from unittest.mock import patch
from zipfile import ZipFile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from exam.models import ExamProblem, Submission
from exam.tests import ExamBaseTestCase
from judge.sandbox import SandboxResult
from judge.tasks import judge_submission, run_sample_tests


def project_zip(entries):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


@override_settings(JUDGE_ENQUEUE_ENABLED=False, CACHES={
    "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "sample_runs": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "project-tests"},
})
class CourseProjectTests(ExamBaseTestCase):
    public = b'def grade(project):\n    return [{"name":"public", "points":10, "max_points":20}]\n'
    hidden = b'def grade(project):\n    return [{"name":"secret", "points":30, "max_points":30, "feedback":"private detail"}]\n'

    def setUp(self):
        super().setUp()
        self.archive = project_zip({"src/main.py": "print(1)"})
        self.auth()
        response = self.client.patch(f"/api/v1/problems/{self.problem2.pk}", {
            "payload": json.dumps({"type": "engineering", "judgeProfile": "script"}),
            "starterArchive": SimpleUploadedFile("starter.zip", self.archive),
            "publicScript": SimpleUploadedFile("public.py", self.public),
            "hiddenScript": SimpleUploadedFile("hidden.py", self.hidden),
        }, format="multipart")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertNotIn(b"private detail", response.content)
        self.exam_id = self.create_exam()["id"]
        self.assemble(self.exam_id)
        ExamProblem.objects.filter(exam_id=self.exam_id, problem=self.problem2).update(score=100)
        self.url = f"/api/v1/my/exams/{self.exam_id}/problems/{self.problem2.id}"
        self.auth(self.student_token)

    def upload(self, endpoint, data):
        return self.client.post(self.url + "/" + endpoint, {
            "archive": SimpleUploadedFile("project.zip", data),
        }, format="multipart")

    def test_invalid_upload_does_not_consume_attempt(self):
        response = self.upload("submissions", project_zip({"../outside": "invalid"}))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Submission.objects.filter(exam_id=self.exam_id).exists())

    @override_settings(JUDGE_ENQUEUE_ENABLED=True)
    @patch("judge.project_scoring.run_script_sandbox")
    @patch("exam.views.run_sample_tests.apply_async")
    def test_only_public_code_downloads_and_runs(self, enqueue, sandbox):
        self.assertEqual(self.client.get(self.url + "/project-files/public.py").content, self.public)
        self.assertEqual(self.client.get(self.url + "/project-files/starter.zip").content, self.archive)
        self.assertEqual(self.client.get(self.url + "/project-files/hidden.py").status_code, 404)
        response = self.upload("sample-runs", self.archive)
        self.assertEqual(response.status_code, 202, response.content)
        poll = self.url + "/sample-runs/" + response.json()["runId"]
        self.assertEqual(self.client.get(poll).json(), {"status": "queued"})
        sandbox.return_value = SandboxResult("", [{"name": "public", "points": 10, "max_points": 20}])
        run_sample_tests.run(*enqueue.call_args.kwargs["args"])
        self.assertEqual(sandbox.call_args.args[:2], ({"src/main.py": b"print(1)"}, self.public.decode()))
        self.assertEqual(self.client.get(poll).json()["cases"][0]["earnedPoints"], 10)
        self.assertFalse(Submission.objects.filter(exam_id=self.exam_id).exists())

    @patch("judge.project_scoring.run_script_sandbox")
    def test_formal_score_uses_snapshot_and_hides_private_details(self, sandbox):
        response = self.upload("submissions", self.archive)
        self.assertEqual(response.status_code, 201, response.content)
        submission = Submission.objects.get(pk=response.json()["submission"]["id"])
        self.assertEqual(bytes(submission.project.archive), self.archive)
        self.problem2.project_hidden = "replaced later"
        self.problem2.save(update_fields=["project_hidden"])
        sandbox.side_effect = [
            SandboxResult("", [{"name": "public", "points": 10, "max_points": 20}]),
            SandboxResult("", [{"name": "secret", "points": 30, "max_points": 30, "feedback": "private detail"}]),
        ]
        judge_submission.run(submission.id)
        self.assertEqual(sandbox.call_args.args[1], self.hidden.decode())
        detail_url = f"/api/v1/submissions/{submission.id}"
        student = self.client.get(detail_url).json()
        self.assertEqual(student["score"], 80)
        self.assertFalse(student["needsReview"])
        self.assertEqual(student["cases"][1]["name"], "隐藏用例 #2")
        self.assertNotIn("errorExcerpt", student["cases"][1])
        self.auth()
        teacher = self.client.get(detail_url).json()
        self.assertEqual(teacher["cases"][1]["errorExcerpt"], "private detail")
        self.assertEqual(self.client.patch(detail_url + "/project-review", {}, format="json").status_code, 404)

    @override_settings(JUDGE_ENQUEUE_ENABLED=True)
    @patch("judge.project_scoring.run_script_sandbox")
    @patch("exam.views.run_sample_tests.apply_async")
    def test_web_workspace_persists_and_freezes_uploaded_template(self, enqueue, sandbox):
        self.problem2.project_template = project_zip({"src/main.py": "print(0)", "data.bin": b"\x00\xff"})
        self.problem2.save(update_fields=["project_template"])
        url = self.url + "/project-workspace"
        starting = self.client.get(url).json()
        self.assertEqual(starting["files"][0]["path"], "src/main.py")
        self.assertEqual(starting["fixedFiles"], ["data.bin"])

        def revision(model):
            return {"workspaceVersion": model["version"],
                    "workspaceRevisions": {file["path"]: file["revision"] for file in model["files"]}}

        updated = self.client.put(url, {
            **revision(starting), "files": {"src/main.py": "print(42)", "Makefile": "all:\n\ttrue\n"},
        }, format="json")
        self.assertEqual(updated.status_code, 200, updated.content)
        saved = updated.json()
        self.assertEqual(self.client.get(url).json(), saved)
        self.assertEqual(self.client.put(url, {**revision(starting), "files": {}}, format="json").status_code, 409)
        self.assertEqual(self.client.post(self.url + "/submissions", revision(starting), format="json").status_code, 409)

        other_token = self.login(self.other_student.username)
        self.auth(other_token)
        self.assertEqual(self.client.get(url).json()["files"], starting["files"])
        self.auth(self.student_token)

        preview = self.client.post(self.url + "/sample-runs", revision(saved), format="json")
        self.assertEqual(preview.status_code, 202, preview.content)
        sandbox.return_value = SandboxResult("", [{"name": "public", "points": 1, "max_points": 1}])
        run_sample_tests.run(*enqueue.call_args.kwargs["args"])
        self.assertEqual(sandbox.call_args.args[0]["src/main.py"], b"print(42)")
        self.assertEqual(sandbox.call_args.args[0]["data.bin"], b"\x00\xff")
        self.assertFalse(Submission.objects.filter(exam_id=self.exam_id).exists())

        response = self.client.post(self.url + "/submissions", revision(saved), format="json")
        self.assertEqual(response.status_code, 201, response.content)
        submission = Submission.objects.get(pk=response.json()["submission"]["id"])
        with ZipFile(io.BytesIO(bytes(submission.project.archive))) as snapshot:
            self.assertEqual(snapshot.read("src/main.py"), b"print(42)")
            self.assertIn("Makefile", snapshot.namelist())
        self.client.put(url, {**revision(saved), "files": {"src/main.py": "print(99)"}}, format="json")
        with ZipFile(io.BytesIO(bytes(submission.project.archive))) as snapshot:
            self.assertEqual(snapshot.read("src/main.py"), b"print(42)")
