from django.urls import path

from .views import PersonaInputCreateView, health

urlpatterns = [
    path("health/", health, name="personas-health"),
    path("inputs/", PersonaInputCreateView.as_view(), name="personas-input-create"),
]
