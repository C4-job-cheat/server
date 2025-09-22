from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('main_app/', include('main_app.urls')),
    path('api/personas/', include('personas.urls')),
    path('api/cover-letters/', include('cover_letters.urls')),
    path('api/interviews/', include('interviews.urls')),
    path('api/job-search/', include('job_search.urls')),
]
