from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/practice/problems", views.PracticeProblemListView.as_view(),
         name="practice_problems"),
    path("api/v1/practice/problems/<int:problem_id>",
         views.PracticeProblemDetailView.as_view(), name="practice_problem_detail"),
    path("api/v1/practice/problems/<int:problem_id>/submissions",
         views.PracticeSubmissionView.as_view(), name="practice_submissions"),
    path("api/v1/practice/submissions/<int:submission_id>",
         views.PracticeSubmissionDetailView.as_view(), name="practice_submission_detail"),
    path("api/v1/practice/problems/<int:problem_id>/comments",
         views.PracticeCommentView.as_view(), name="practice_comments"),
    path("api/v1/practice/comments/<int:comment_id>",
         views.PracticeCommentDetailView.as_view(), name="practice_comment_detail"),
]
