from django.urls import path

from . import views

urlpatterns = [
    # 管理端（教师 / 管理员）
    path("api/v1/exams", views.ExamListView.as_view(), name="exams"),
    path("api/v1/exams/<int:exam_id>", views.ExamDetailView.as_view(), name="exam_detail"),
    path("api/v1/exams/<int:exam_id>/problems", views.ExamProblemsView.as_view(), name="exam_problems"),
    path("api/v1/exams/<int:exam_id>/candidates", views.ExamCandidatesView.as_view(), name="exam_candidates"),
    path("api/v1/exams/<int:exam_id>/submissions", views.ExamSubmissionsView.as_view(), name="exam_submissions"),
    path("api/v1/exams/<int:exam_id>/<str:action>", views.ExamActionView.as_view(), name="exam_action"),
    # 学生侧（登录即可）
    path("api/v1/my/exams", views.MyExamListView.as_view(), name="my_exams"),
    path("api/v1/my/exams/<int:exam_id>", views.MyExamDetailView.as_view(), name="my_exam_detail"),
    path("api/v1/my/exams/<int:exam_id>/submissions", views.MyExamSubmissionsView.as_view(), name="my_exam_submissions"),
    path(
        "api/v1/my/exams/<int:exam_id>/problems/<int:problem_id>/submissions",
        views.MySubmissionView.as_view(),
        name="my_submission",
    ),
]
