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
    path('pricing/', views_subscription.pricing, name='pricing'),
    path('subscription/success/', views_subscription.subscription_success, name='subscription_success'),
    path('subscription-status/', views_subscription.subscription_status, name='subscription_status'),
    path('subscription/debug/', views_subscription.check_subscription_status, name='subscription_debug'),
    path('subscription/cancel/', views_subscription.cancel_subscription, name='cancel_subscription'),
    path('polar/webhook', views_subscription.polar_webhook, name='polar_webhook'),
]