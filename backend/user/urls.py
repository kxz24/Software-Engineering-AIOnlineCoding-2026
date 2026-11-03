from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/user", views.get_user_info, name="get_user_info"),
    path("api/v1/register", views.RegisterView.as_view(), name="register"),
    path("api/v1/login", views.LoginView.as_view(), name="login"),
    path("api/v1/logout", views.logout, name="logout"),
    path("api/v1/users", views.UserListView.as_view(), name="users"),
    path(
        "api/v1/users/import",
        views.UserImportView.as_view(),
        name="users_import",
    ),
    path(
        "api/v1/users/<int:user_id>",
        views.UserDetailView.as_view(),
        name="user_detail",
    ),
    path("api/v1/audit", views.AuditLogView.as_view(), name="audit"),
]
