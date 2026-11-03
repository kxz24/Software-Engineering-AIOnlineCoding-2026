from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from user.controllers import record_audit

from .models import Problem, TestSample


def list_problems(keyword=None, problem_type=None, language=None):
    """
    题目列表：按标题 / 题面搜索、按题型与语言过滤，附样例 / 隐藏用例计数
    """
    query = Problem.objects.all()
    if keyword:
        query = query.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    if problem_type:
        query = query.filter(type=problem_type)
    if language:
        query = query.filter(language=language)
    return query.order_by("-updated")


def get_problem(problem_id):
    try:
        problem = Problem.objects.get(id=problem_id)
        return problem, True
    except ObjectDoesNotExist:
        return "not found", False
    except Exception as e:
        print(e)
        return "errors", False


def problem_summary(problem):
    """列表用的题目摘要（不含题面全文与用例内容）"""
    return {
        "id": problem.id,
        "title": problem.title,
        "type": problem.type,
        "language": problem.language,
        "difficulty": problem.difficulty,
        "image": problem.image,
        "sampleCount": problem.samples.filter(is_sample=True).count(),
        "hiddenCount": problem.samples.filter(is_sample=False).count(),
        "updated": problem.updated,
    }


def problem_detail(problem):
    """详情：题面全文 + 全部用例（仅教师 / 管理员可见，含隐藏测试）"""
    return {
        **problem_summary(problem),
        "description": problem.description,
        "starterCode": problem.starter_code,
        "createdBy": problem.created_by.username if problem.created_by else "",
        "samples": [
            {
                "id": sample.id,
                "name": sample.name,
                "input": sample.input_data,
                "expected": sample.expected_output,
                "isSample": sample.is_sample,
            }
            for sample in problem.samples.all()
        ],
    }


def replace_samples(problem, samples):
    """
    用给定列表整体替换题目的用例（编辑器按行提交，简单可靠）。
    samples 为 dict 列表，键与 problem_detail 的序列化格式一致。
    """
    problem.samples.all().delete()
    for sample in samples:
        TestSample.objects.create(
            problem=problem,
            name=str(sample.get("name") or "").strip() or "未命名用例",
            input_data=str(sample.get("input") or ""),
            expected_output=str(sample.get("expected") or ""),
            is_sample=bool(sample.get("isSample", True)),
        )


def create_problem(operator, fields, samples):
    """
    创建题目。fields 为已校验的字段 dict，samples 为用例列表。
    """
    try:
        problem = Problem.objects.create(created_by=operator, **fields)
        replace_samples(problem, samples)
        record_audit(operator, "problem.create", f"创建题目「{problem.title}」")
        return problem, True
    except Exception as e:
        print(e)
        return "errors", False


def update_problem(operator, problem, fields, samples=None):
    """
    编辑题目字段；samples 非 None 时整体替换用例。
    """
    try:
        for key, value in fields.items():
            setattr(problem, key, value)
        problem.save()
        if samples is not None:
            replace_samples(problem, samples)
        record_audit(operator, "problem.update", f"编辑题目「{problem.title}」")
        return problem, True
    except Exception as e:
        print(e)
        return "errors", False


def delete_problem(operator, problem):
    """
    删除题目（级联删除用例）
    """
    try:
        title = problem.title
        problem.delete()
        record_audit(operator, "problem.delete", f"删除题目「{title}」")
        return True
    except Exception as e:
        print(e)
        return False
