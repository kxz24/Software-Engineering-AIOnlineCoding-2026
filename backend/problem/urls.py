from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/problems", views.ProblemListView.as_view(), name="problems"),
    path("api/v1/problems/import-project", views.ProjectImportView.as_view(), name="project_import"),
    path(
        "api/v1/problems/<int:problem_id>",
        views.ProblemDetailView.as_view(),
        name="problem_detail",
    ),
]
