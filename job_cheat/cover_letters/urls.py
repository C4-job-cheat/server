from django.urls import path
from . import views

urlpatterns = [
    path("health/", views.health, name="cover-letters-health"),
    
    # 1. 자기소개서 input 작성
    path("", views.get_persona_card, name="cover-letters-persona-card"),
    
    # 2. 자기소개서 생성
    path("create/", views.create_cover_letter, name="cover-letters-create"),
    
    # 3. 자기소개서 목록 조회
    path("list/", views.list_cover_letters, name="cover-letters-list"),
    
    # 4. 자기소개서 상세 조회
    path("list/<str:cover_letter_id>/", views.get_cover_letter_detail, name="cover-letters-detail"),
]


