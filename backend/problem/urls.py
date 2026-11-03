from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/problems", views.ProblemListView.as_view(), name="problems"),
    path(
        "api/v1/problems/<int:problem_id>",
        views.ProblemDetailView.as_view(),
        name="problem_detail",
    ),
]
