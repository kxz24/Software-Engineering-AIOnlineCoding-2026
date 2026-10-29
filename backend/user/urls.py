from django.urls import path

from . import views

urlpatterns = [
    path("api/v1/user", views.get_user_info, name="get_user_info"),
    path("api/v1/login", views.LoginView.as_view(), name="login"),
    path("api/v1/logout", views.logout, name="logout"),
]
