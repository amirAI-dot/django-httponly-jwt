"""The test project's pages: each stage adds the ones it tests."""

from django.urls import path

from httponly_jwt.views import RefreshView, SignOutView
from tests.project import views

urlpatterns = [
    path('signed-in/', views.SignedIn.as_view()),
    path('anybody/', views.Anybody.as_view()),
    path('anybody-more/', views.AnybodyMoreIfSignedIn.as_view()),
    path('sets-session/', views.SetsTheSessionItself.as_view()),
    path('clears-session/', views.ClearsTheSessionItself.as_view()),
    path('sign-in/', views.SignIn.as_view()),
    path('claims/', views.Claims.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/sign-out/', SignOutView.as_view()),
]
