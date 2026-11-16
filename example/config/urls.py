"""Every address the example answers."""

from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from accounts import views
from httponly_jwt.views import RefreshView, SignOutView

urlpatterns = [
    # The project's own: how a person proves who they are.
    path('auth/code/', views.SendCode.as_view()),
    path('auth/sign-in/', views.SignIn.as_view()),
    # The library's.
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
    # What a signed-in person reads.
    path('me/', views.Me.as_view()),
    path('schema/', SpectacularAPIView.as_view()),
]
