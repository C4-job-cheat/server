from django.urls import path
from .views import VerifyFirebaseIdTokenView


urlpatterns = [
    path('auth/verify/', VerifyFirebaseIdTokenView.as_view(), name='api-auth-verify'),
]


