from django.urls import path
from .views import health, get_user_recommendations_view, get_job_detail_with_recommendation_view, add_scrap_view, remove_scrap_view, get_scraped_jobs_view


urlpatterns = [
    path('health/', health, name='job-search-health'),
    path('recommendations/', get_user_recommendations_view, name='recommendations'),
    path('recommendations/<str:job_posting_id>/', get_job_detail_with_recommendation_view, name='get-job-detail-with-recommendation'),
    path('scrap/add/', add_scrap_view, name='job-search-add-scrap'),
    path('scrap/remove/', remove_scrap_view, name='job-search-remove-scrap'),
    path('scrap/list/', get_scraped_jobs_view, name='job-search-scrap-list'),

]


