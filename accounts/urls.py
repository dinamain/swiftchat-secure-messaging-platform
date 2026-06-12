from django.urls import path
from .views import RegisterView, ProfileView, LogoutView, CustomLoginView
from rest_framework_simplejwt.views import(
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import UserListView
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("token/refresh/",TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("custom-login/", CustomLoginView.as_view(), name="custom_login"),
    path("users/", UserListView.as_view(), name="list_users"),
]