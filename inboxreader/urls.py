from django.urls import path
from . import views
from .views import evaluate_resumes
urlpatterns = [
    path('fetch-attachments/', views.fetch_attachments, name='fetch_attachments'),
    path('cv-evaluation/', evaluate_resumes, name='cv_evaluation'),
    path('download-cv/', views.download_cv, name='download_cv'),
    path('view-cv/', views.view_cv, name='view_cv'),
]
