from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload'),
    path('yournotes/', views.yournotes, name='yournotes'),
    path('yournotes/<int:file_id>/delete', views.yournotes, name='delete_file'),
    path('settings/', views.settings, name='settings'),
    path('toggle-dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode')

]