from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserSubscription, Plan
from django.utils import timezone

def get_or_create_free_plan():
    """Helper function to ensure free plan exists"""
    try:
        free_plan = Plan.objects.get(name='free')
    except Plan.DoesNotExist:
        free_plan = Plan.objects.create(
            name='free',
            billing_period='free',
            is_free=True,
            price=0,
            description='Free tier with basic features',
            # Set reasonable limits for free plan
            pdf_uploads_per_month=4,
            pdf_max_size_mb=5,
            pdf_max_pages=10,
            audio_uploads_per_month=1,
            audio_max_size_mb=10,
            audio_max_length_min=10,
            youtube_links_per_month=1,
            youtube_max_length_min=10,
            quizzes_per_month=5,
            summary_regenerations_per_file=1,
            chatbot_messages_per_file=10
        )
    return free_plan

@receiver(post_save, sender=User)
def create_user_subscription(sender, instance, created, **kwargs):
    """
    Signal to automatically create a UserSubscription with free plan for new users
    """
    if created:
        # Get or create the free plan
        free_plan = get_or_create_free_plan()
        
        # Create the subscription
        UserSubscription.objects.create(
            user=instance,
            plan=free_plan,
            status='active',
            is_active=True,
            current_period_start=timezone.now(),
            current_period_end=None  # Free plan doesn't expire
        )
