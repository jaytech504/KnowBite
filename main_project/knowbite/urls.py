from django.urls import path
from . import views
from . import views_subscription

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('upload/', views.upload_file, name='upload'),
    path('yournotes/', views.yournotes, name='yournotes'),
    path('yournotes/<int:file_id>/delete', views.yournotes, name='delete_file'),
    path('settings/', views.settings, name='settings'),
    path('toggle-dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode'),
    path('pricing/', views_subscription.pricing, name='pricing'),
    path('subscription/success/', views_subscription.subscription_success, name='subscription_success'),
    path('subscription-status/', views_subscription.subscription_status, name='subscription_status'),
    path('subscription/debug/', views_subscription.check_subscription_status, name='subscription_debug'),
    path('paddle/webhook/', views_subscription.paddle_webhook, name='paddle_webhook'),
    path('subscription/cancel/', views_subscription.cancel_subscription, name='cancel_subscription'),
]