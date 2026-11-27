from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/submissions/<int:submission_id>/archive", views.ProjectArchiveView.as_view()),
    path(
        "api/v1/submissions/<int:submission_id>",
        views.SubmissionDetailView.as_view(),
        name="submission_detail",
    ),
]
