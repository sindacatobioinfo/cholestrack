"""
URL configuration for AI Agent app.
"""

from django.urls import path
from . import views

app_name = 'ai_agent'

urlpatterns = [
    # Main chat interface
    path('', views.chat_interface, name='chat_interface'),

    # Chat actions
    path('send-message/', views.send_message, name='send_message'),
    path('new-session/', views.new_session, name='new_session'),
    path('session/<uuid:session_id>/', views.load_session, name='load_session'),

    # Analysis jobs
    path('start-job/', views.start_analysis_job, name='start_job'),
    path('job-status/<uuid:job_id>/', views.job_status, name='job_status'),
    path('download-report/<uuid:job_id>/', views.download_report, name='download_report'),
]
