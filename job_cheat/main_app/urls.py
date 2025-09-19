from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('auth/verify/', views.VerifyFirebaseIdTokenView.as_view(), name='auth-verify'),
]


