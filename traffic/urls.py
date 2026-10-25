from django.urls import path
from . import views

app_name = 'traffic'

urlpatterns = [
    # Main Views
    path('', views.dashboard_view, name='dashboard'),
    path('intersection/<int:pk>/', views.intersection_detail_view, name='detail'),
    path('compare/', views.compare_view, name='compare'),
    path('upload/', views.upload_view, name='upload'),
    path('about/', views.about_view, name='about'),
    path('download-sample/', views.download_sample_csv, name='download_sample'),

    # JSON API Endpoints for Chart.js
    path('api/peaks/', views.api_peaks, name='api_peaks'),
    path('api/profile/<int:pk>/', views.api_hourly_profile, name='api_profile'),
    path('api/compare/', views.api_compare, name='api_compare'),
]

