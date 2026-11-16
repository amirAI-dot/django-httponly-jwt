"""The test project's pages: each stage adds the ones it tests."""

from django.urls import path

from tests.project import views

urlpatterns = [
    path('signed-in/', views.SignedIn.as_view()),
    path('anybody/', views.Anybody.as_view()),
    path('anybody-more/', views.AnybodyMoreIfSignedIn.as_view()),
]
