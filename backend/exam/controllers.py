"""考试业务的底层操作：创建 / 组卷 / 名单 / 发布 / 提交。"""

from django.utils import timezone

from problem.models import Problem
from user.controllers import record_audit
from user.models import User

from .models import Exam, ExamCandidate, ExamProblem, Submission


def _to_bool(value):
    return str(value).lower() in ("1", "true", "yes")


def _iso(value):
    """datetime → ISO 字符串（None 保持为 None）"""
    return value.isoformat() if value else None


def _student_status(exam, now=None):
    """按当前时间推导学生侧状态：upcoming / ongoing / finished"""
    now = now or timezone.now()
    if not exam.start_time or not exam.end_time:
        return "upcoming"
    if now < exam.start_time:
        return "upcoming"
    if now <= exam.end_time:
        return "ongoing"
    return "finished"


def open_to_all(exam):
    """名单为空表示全体学生可参加"""
    return not exam.exam_candidates.exists()


def is_candidate(exam, user):
    """user 是否为本场考试的考生（名单成员，或名单为空时的任意学生）"""
    if open_to_all(exam):
        return user.role == User.ROLE_STUDENT
    return exam.exam_candidates.filter(student=user).exists()


# ---------------------------------------------------------------------------
# 教师侧：增删改查与状态流转
# ---------------------------------------------------------------------------

def list_exams(status=None):
    exams = Exam.objects.all()
    if status:
        exams = exams.filter(status=status)
    return exams


def get_exam(exam_id):
    exam = Exam.objects.filter(id=exam_id).first()
    return (exam, True) if exam else ("考试不存在", False)


def create_exam(user, fields):
    exam = Exam.objects.create(title=fields["title"], created_by=user, **{
        key: value for key, value in fields.items() if key != "title"
    })
    record_audit(user, "exam.create", f"{exam.id} {exam.title}")
    return exam, True


def update_exam(user, exam, fields):
    for key, value in fields.items():
        setattr(exam, key, value)
    exam.save()
    record_audit(user, "exam.update", f"{exam.id} {exam.title}")
    return exam, True


def set_exam_problems(user, exam, items):
    """整体替换组卷列表；items 形如 [{problemId, score}]，顺序即题序。"""
    problem_ids = [item["problemId"] for item in items]
    if len(problem_ids) != len(set(problem_ids)):
        return "题目重复", False
    problems = {
        p.id: p for p in Problem.objects.filter(id__in=problem_ids)
    }
    missing = [pid for pid in problem_ids if pid not in problems]
    if missing:
        return f"题目不存在：{missing}", False

    exam.exam_problems.all().delete()
    ExamProblem.objects.bulk_create([
        ExamProblem(exam=exam, problem=problems[item["problemId"]], order=index,
                    score=item.get("score", 100))
        for index, item in enumerate(items)
    ])
    record_audit(user, "exam.problems", f"{exam.id} 共 {len(items)} 题")
    return True, True


def set_candidates(user, exam, usernames):
    """整体替换考生名单；传空列表表示全体学生。"""
    students = User.objects.filter(username__in=usernames, role=User.ROLE_STUDENT)
    found = {s.username for s in students}
    missing = [name for name in usernames if name not in found]
    if missing:
        return f"以下账号不存在或不是学生：{missing}", False

    exam.exam_candidates.all().delete()
    ExamCandidate.objects.bulk_create([
        ExamCandidate(exam=exam, student=student) for student in students
    ])
    record_audit(user, "exam.candidates", f"{exam.id} 名单 {len(usernames)} 人")
    return True, True


def publish_exam(user, exam):
    """发布前校验时间、题目与名单完整性（SRS 3.3.2-4）。"""
    if exam.status == Exam.STATUS_PUBLISHED:
        return "考试已发布", False
    if exam.status == Exam.STATUS_ARCHIVED:
        return "已归档的考试不能发布", False
    if not exam.start_time or not exam.end_time:
        return "请先设置开始与结束时间", False
    if exam.end_time <= exam.start_time:
        return "结束时间必须晚于开始时间", False
    if not exam.exam_problems.exists():
        return "请先从题库选题组卷", False
    if not open_to_all(exam) and not exam.exam_candidates.exists():
        return "考生名单为空", False

    exam.status = Exam.STATUS_PUBLISHED
    exam.save()
    record_audit(user, "exam.publish", f"{exam.id} {exam.title}")
    return True, True


def withdraw_exam(user, exam):
    """撤回发布：仅开始前允许，撤回后回到草稿可继续编辑。"""
    if exam.status != Exam.STATUS_PUBLISHED:
        return "只有已发布的考试可以撤回", False
    if exam.start_time and timezone.now() >= exam.start_time:
        return "考试已开始，配置已冻结", False

    exam.status = Exam.STATUS_DRAFT
    exam.save()
    record_audit(user, "exam.withdraw", f"{exam.id} {exam.title}")
    return True, True


def archive_exam(user, exam):
    """归档：考试结束后才能归档。"""
    if exam.status != Exam.STATUS_PUBLISHED:
        return "只有已发布的考试可以归档", False
    if not exam.end_time or timezone.now() < exam.end_time:
        return "考试尚未结束，不能归档", False

    exam.status = Exam.STATUS_ARCHIVED
    exam.save()
    record_audit(user, "exam.archive", f"{exam.id} {exam.title}")
    return True, True


def delete_exam(user, exam):
    if exam.status != Exam.STATUS_DRAFT:
        return "只有草稿可以删除，已发布的考试请先撤回", False
    title = exam.title
    exam.delete()
    record_audit(user, "exam.delete", f"{exam.title}")
    return True, True


# ---------------------------------------------------------------------------
# 序列化
# ---------------------------------------------------------------------------

def exam_summary(exam, now=None):
    """管理端列表条目"""
    now = now or timezone.now()
    student_status = _student_status(exam, now)
    candidate_count = (
        User.objects.filter(role=User.ROLE_STUDENT).count()
        if open_to_all(exam) else exam.exam_candidates.count()
    )
    return {
        "id": exam.id,
        "title": exam.title,
        "course": exam.course,
        "status": exam.status,
        "studentStatus": student_status,
        "startTime": _iso(exam.start_time),
        "endTime": _iso(exam.end_time),
        "durationMinutes": exam.duration_minutes,
        "submitLimit": exam.submit_limit,
        "aiMode": exam.ai_mode,
        "problemCount": exam.exam_problems.count(),
        "candidateCount": candidate_count,
        "openToAll": open_to_all(exam),
        "submissionCount": exam.submissions.count(),
        "updated": _iso(exam.updated),
    }


def exam_detail(exam):
    """管理端详情：含组卷与名单"""
    detail = exam_summary(exam)
    detail.update({
        "description": exam.description,
        "notice": exam.notice,
        "createdBy": exam.created_by.username if exam.created_by else "",
        "problems": [
            {
                "problemId": item.problem_id,
                "order": item.order,
                "score": item.score,
                "title": item.problem.title,
                "type": item.problem.type,
                "language": item.problem.language,
                "difficulty": item.problem.difficulty,
                "sampleCount": item.problem.samples.filter(is_sample=True).count(),
                "hiddenCount": item.problem.samples.filter(is_sample=False).count(),
            }
            for item in exam.exam_problems.select_related("problem")
        ],
        "candidates": list(
            exam.exam_candidates.values_list("student__username", flat=True)
        ),
    })
    return detail


def _problem_for_student(item):
    """学生视角的题目：题面、初始代码、样例测试；隐藏测试不下发。"""
    problem = item.problem
    return {
        "problemId": problem.id,
        "order": item.order,
        "score": item.score,
        "title": problem.title,
        "type": problem.type,
        "language": problem.language,
        "difficulty": problem.difficulty,
        "description": problem.description,
        "starterCode": problem.starter_code,
        "samples": [
            {"name": s.name, "input": s.input_data, "expected": s.expected_output}
            for s in problem.samples.filter(is_sample=True)
        ],
    }


# ---------------------------------------------------------------------------
# 学生侧：考试列表 / 详情 / 提交
# ---------------------------------------------------------------------------

def student_exams(student):
    """学生可见的考试：已发布（含归档）且本人在名单内（或名单为空）。"""
    exams = Exam.objects.exclude(status=Exam.STATUS_DRAFT)
    visible = [exam for exam in exams if is_candidate(exam, student)]
    result = []
    for exam in visible:
        summary = exam_summary(exam)
        summary["mySubmissions"] = exam.submissions.filter(student=student).count()
        result.append(summary)
    return result


def student_exam_detail(student, exam):
    """学生视角的考试详情；不可见时返回 (reason, False)。"""
    if exam.status == Exam.STATUS_DRAFT:
        return "考试不存在", False
    if not is_candidate(exam, student):
        return "不在本场考试的名单中", False

    detail = {
        "id": exam.id,
        "title": exam.title,
        "course": exam.course,
        "description": exam.description,
        "notice": exam.notice,
        "status": _student_status(exam),
        "startTime": _iso(exam.start_time),
        "endTime": _iso(exam.end_time),
        "durationMinutes": exam.duration_minutes,
        "submitLimit": exam.submit_limit,
        "aiMode": exam.ai_mode,
        "problems": [
            _problem_for_student(item) for item in exam.exam_problems.select_related("problem")
        ],
    }
    return detail, True


def submission_count(exam, problem_id, student):
    """某学生某题已用的提交次数"""
    return Submission.objects.filter(
        exam=exam, problem_id=problem_id, student=student
    ).count()


def create_submission(student, exam, problem_id, code, language):
    """
    学生提交代码。当前阶段只存档不判分，判题服务接入后由其消费。

    返回 (submission, True) 或 (reason, http_status, False)。
    """
    if exam.status != Exam.STATUS_PUBLISHED:
        return "考试未发布或已归档", 403, False
    now = timezone.now()
    if exam.start_time and now < exam.start_time:
        return "考试尚未开始", 400, False
    if exam.end_time and now > exam.end_time:
        return "考试已结束，不能再提交", 400, False
    if not is_candidate(exam, student):
        return "不在本场考试的名单中", 403, False

    item = exam.exam_problems.filter(problem_id=problem_id).select_related("problem").first()
    if not item:
        return "本场考试没有这道题", 404, False

    used = submission_count(exam, problem_id, student)
    if used >= exam.submit_limit:
        return f"该题提交次数已用完（每题 {exam.submit_limit} 次）", 400, False

    submission = Submission.objects.create(
        exam=exam, problem=item.problem, student=student,
        code=code, language=language or item.problem.language,
    )
    record_audit(student, "submission.create",
                 f"{exam.id}#{problem_id} 第 {used + 1} 次")
    return submission, 200, True


def _submission_brief(submission, with_code=False):
    brief = {
        "id": submission.id,
        "examId": submission.exam_id,
        "problemId": submission.problem_id,
        "problemTitle": submission.problem.title,
        "username": submission.student.username,
        "nickname": submission.student.nickname,
        "language": submission.language,
        "status": submission.status,
        "created": _iso(submission.created),
    }
    if with_code:
        brief["code"] = submission.code
    return brief


def exam_submissions(exam, problem_id=None):
    """管理端：本场考试的提交记录（默认不含代码正文，前端点开再看）"""
    queryset = exam.submissions.select_related("student", "problem")
    if problem_id:
        queryset = queryset.filter(problem_id=problem_id)
    return [_submission_brief(s) for s in queryset]


def my_submissions(student, exam):
    """学生侧：我在本场考试的提交记录（含代码正文）"""
    return [
        _submission_brief(s, with_code=True)
        for s in exam.submissions.filter(student=student).select_related("student", "problem")
    ]
