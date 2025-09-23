from django.urls import path
from .views import VerifyFirebaseIdTokenView, SyncFirebaseUserView


urlpatterns = [
    path('auth/verify/', VerifyFirebaseIdTokenView.as_view(), name='api-auth-verify'),
    path('auth/sync/', SyncFirebaseUserView.as_view(), name='api-auth-sync'),
]


