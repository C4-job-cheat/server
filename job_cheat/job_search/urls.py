from django.urls import path
from .views import health, save_job_posting, vectorize_job_postings, save_persona_recommendations_view, calculate_persona_job_scores_view, calculate_persona_job_scores_from_data_view


urlpatterns = [
    path('health/', health, name='job-search-health'),
    path('save-persona-recommendation/', save_persona_recommendations_view, name='save-persona-recommendations-with-skill-score'),
    # TODO: 삭제 예정 - 테스트용 엔드포인트들
    path('save-job/', save_job_posting, name='save-job-posting'),
    path('vectorize-jobs/', vectorize_job_postings, name='vectorize-job-postings'),
    path('calculate-persona-job-scores/', calculate_persona_job_scores_view, name='calculate-persona-job-scores'),
    path('calculate-persona-job-scores-from-data/', calculate_persona_job_scores_from_data_view, name='calculate-persona-job-scores-from-data'),
]


