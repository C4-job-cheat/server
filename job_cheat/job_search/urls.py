from django.urls import path
from .views import health, save_job_posting, vectorize_job_postings, calculate_persona_job_scores_view, calculate_persona_job_scores_from_data_view, get_user_recommendations_view, get_job_detail_with_recommendation_view, add_scrap_view, remove_scrap_view, get_scraped_jobs_view


urlpatterns = [
    path('health/', health, name='job-search-health'),
    path('recommendations/', get_user_recommendations_view, name='recommendations'),
    path('recommendations/<str:job_posting_id>/', get_job_detail_with_recommendation_view, name='get-job-detail-with-recommendation'),
    path('scrap/add/', add_scrap_view, name='job-search-add-scrap'),
    path('scrap/remove/', remove_scrap_view, name='job-search-remove-scrap'),
    path('scrap/list/', get_scraped_jobs_view, name='job-search-scrap-list'),

    # TODO: 삭제 예정 - 테스트용 엔드포인트들
    path('save-job/', save_job_posting, name='save-job-posting'),
    path('vectorize-jobs/', vectorize_job_postings, name='vectorize-job-postings'),
    path('calculate-persona-job-scores/', calculate_persona_job_scores_view, name='calculate-persona-job-scores'),
    path('calculate-persona-job-scores-from-data/', calculate_persona_job_scores_from_data_view, name='calculate-persona-job-scores-from-data'),
]


