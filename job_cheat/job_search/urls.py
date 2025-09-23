from django.urls import path
from .views import health, save_job_posting, vectorize_job_postings, match_jobs_by_persona, match_jobs_by_persona_data


urlpatterns = [
    path('health/', health, name='job-search-health'),
    # TODO: 삭제 예정 - 테스트용 엔드포인트들
    path('save-job/', save_job_posting, name='save-job-posting'),
    path('vectorize-jobs/', vectorize_job_postings, name='vectorize-job-postings'),
    path('match-by-persona/', match_jobs_by_persona, name='match-jobs-by-persona'),
    path('match-by-persona-data/', match_jobs_by_persona_data, name='match-jobs-by-persona-data'),
]


