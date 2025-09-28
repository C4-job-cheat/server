from django.urls import path
from .views import (
    health,
    get_interview_history,
    get_interview_preparation,
    generate_interview_questions_view,
    submit_answer_and_get_next_view,
    get_question_detail_view,
)


urlpatterns = [
    path('health/', health, name='interviews-health'),
    path('history/', get_interview_history, name='interviews-history'),
    path('preparation/', get_interview_preparation, name='interviews-preparation'),
    path('questions/generate/', generate_interview_questions_view, name='interviews-generate-questions'),
    path('answers/submit-and-next/', submit_answer_and_get_next_view, name='interviews-submit-and-next'),
    path('sessions/<str:interview_session_id>/questions/<str:question_id>/', 
         get_question_detail_view, name='interviews-question-detail'),
]


