from django.urls import path

from .views import (
    PersonaInputCreateView,
    PersonaJsonDownloadView,
    PersonaFileListView,
    health,
)

urlpatterns = [
    path("health/", health, name="personas-health"),
    path("inputs/", PersonaInputCreateView.as_view(), name="personas-input-create"),
    path("json/<str:document_id>/", PersonaJsonDownloadView.as_view(), name="personas-json-download"),
    path("files/", PersonaFileListView.as_view(), name="personas-file-list"),
]
