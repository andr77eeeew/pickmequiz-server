from django.urls import path

from users import views

app_name = "users"

urlpatterns = [
    path("api/register", views.RegistrationAPIView.as_view(), name="register"),
    path("api/login", views.LoginAPIView.as_view(), name="login"),
    path("api/logout", views.LogoutAPIView.as_view(), name="logout"),
    path(
        "api/token/refresh",
        views.CustomTokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path("api/profile", views.UserProfileAPIView.as_view(), name="profile"),
]
