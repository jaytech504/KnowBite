from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Plan, UserSubscription
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
import datetime
import json
from dateutil import parser
from django.utils import timezone
import logging
from .polar_client import PolarClient

logger = logging.getLogger(__name__)
polar_client = PolarClient()

def create_or_update_subscription(user, subscription_id, plan, trial_end=None, 
                                current_period_start=None, current_period_end=None):
    """Helper function to create or update a user subscription"""
    try:
        subscription, created = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                'polar_subscription_id': subscription_id,
                'plan': plan,
                'status': 'trialing' if trial_end else 'active',
                'is_active': True,
                'trial_end': trial_end,
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'last_webhook_received': timezone.now()
            }
        )
        polar_client.update_subscription(subscription_id, plan_id=plan.polar_plan_id)
        logger.info(f"{'Created' if created else 'Updated'} subscription for user {user.email}")
        return subscription
    except Exception as e:
        logger.error(f"Error creating/updating subscription for user {user.email}: {str(e)}")
        return None

@login_required
def pricing(request):
    plans = Plan.objects.all().order_by('price')
    user_subscription = UserSubscription.objects.get(user=request.user)
    
    return render(request, 'knowbite/pricing.html', {
        'plans': plans,
        'current_plan': user_subscription.plan,
    })

@login_required
def subscription_status(request):
    """View to display subscription status"""
    try:
        user_subscription = UserSubscription.objects.select_related('plan').get(user=request.user)
        
        # Check for expired cancelled subscriptions and revert to free plan
        if user_subscription.status == 'canceled' and user_subscription.current_period_end:
            if timezone.now() > user_subscription.current_period_end:
                # Get or create free plan
                from .signals import get_or_create_free_plan
                free_plan = get_or_create_free_plan()
                
                # Update subscription to free plan
                user_subscription.plan = free_plan
                user_subscription.status = 'active'
                user_subscription.is_active = True
                user_subscription.polar_subscription_id = None
                user_subscription.current_period_start = timezone.now()
                user_subscription.current_period_end = None
                user_subscription.save()
                
                logger.info(f"Reverted cancelled subscription to free plan for user {request.user.email}")
        
        # Get fresh subscription data after potential update
        user_subscription.refresh_from_db()
        logger.info(f"Found subscription for user {request.user.email}: {user_subscription.status} - Plan: {user_subscription.plan.name}")
    except UserSubscription.DoesNotExist:
        user_subscription = None
        logger.info(f"No subscription found for user {request.user.email}")
    
    return render(request, 'knowbite/subscription_status.html', 
                 {'user_subscription': user_subscription})

@login_required
def subscription_success(request):
    """Handle successful subscription completion"""
    return render(request, 'knowbite/subscription_success.html')

@login_required
def check_subscription_status(request):
    """Debug endpoint to check subscription status"""
    try:
        subscription = UserSubscription.objects.get(user=request.user)
        status = {
            'has_subscription': True,
            'status': subscription.status,
            'is_active': subscription.is_active,
            'plan': subscription.plan.name if subscription.plan else None,
            'trial_end': subscription.trial_end,
            'current_period_end': subscription.current_period_end,
            'polar_subscription_id': subscription.polar_subscription_id
        }
        logger.info(f"Debug view - Found subscription for user {request.user.email}: {status}")
    except UserSubscription.DoesNotExist:
        status = {
            'has_subscription': False,
            'message': 'No subscription found for user'
        }
        logger.info(f"Debug view - No subscription found for user {request.user.email}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(status)
    return render(request, 'knowbite/subscription_debug.html', {'status': status})

@csrf_exempt
def polar_webhook(request):
    """
    Handle Polar.sh webhook notifications
    """
    if request.method == 'POST':
        try:
            # Verify webhook signature
            signature = request.headers.get('X-Polar-Signature')
            if not signature or not polar_client.verify_webhook(request.body, signature):
                logger.error("Invalid webhook signature")
                return JsonResponse({'status': 'error', 'message': 'Invalid signature'}, status=401)

            payload = json.loads(request.body)
            event_type = payload.get('type')  # Polar uses 'type' instead of 'event_type'
            subscription_id = payload.get('data', {}).get('subscription_id')
            user_email = payload.get('data', {}).get('customer_email')
            plan_id = payload.get('data', {}).get('plan_id')

            user = User.objects.get(email=user_email)
            plan = Plan.objects.get(polar_plan_id=plan_id)

            if event_type == 'subscription.created':
                create_or_update_subscription(
                    user=user,
                    subscription_id=subscription_id,
                    plan=plan,
                    current_period_start=parser.parse(payload.get('data', {}).get('current_period_start')),
                    current_period_end=parser.parse(payload.get('data', {}).get('current_period_end')),
                )
            elif event_type == 'subscription.canceled':
                subscription = UserSubscription.objects.get(user=user)
                subscription.status = 'canceled'
                subscription.is_active = False
                subscription.save()

            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Error processing Polar webhook: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

def parse_iso_date(date_str):
    """Parse ISO format date string to datetime object"""
    if not date_str:
        return None
    try:
        from dateutil.parser import parse
        return parse(date_str)
    except:
        return None

def send_subscription_notification(user_sub, event_type):
    """Send email notifications for subscription events"""
    from django.core.mail import send_mail
    from django.conf import settings
    
    subject_map = {
        'subscription.created': 'Welcome to KnowBite Premium!',
        'subscription.trial_ended': 'Your KnowBite trial has ended',
        'subscription.canceled': 'Your KnowBite subscription has been canceled',
    }
    
    if event_type in subject_map:
        subject = subject_map[event_type]
        message = f"""Hi {user_sub.user.username},

Your KnowBite subscription status has been updated:
- Plan: {user_sub.plan.name if user_sub.plan else 'No Plan'}
- Status: {user_sub.get_subscription_status()}
"""
        
        if event_type == 'subscription.created' and user_sub.is_in_trial():
            message += f"\nYour trial period will end on {user_sub.trial_end.strftime('%B %d, %Y')}"
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user_sub.user.email],
            fail_silently=True,
        )

from django.views.decorators.http import require_POST

@require_POST
@login_required
def cancel_subscription(request):
    try:
        user_subscription = UserSubscription.objects.get(user=request.user)
        if not user_subscription.polar_subscription_id:
            return JsonResponse({'status': 'error', 'message': 'No Polar subscription ID found.'}, status=400)

        try:
            polar_client.cancel_subscription(user_subscription.polar_subscription_id)
            user_subscription.status = 'canceled'
            user_subscription.is_active = False
            user_subscription.canceled_at = timezone.now()
            user_subscription.save()
            logger.info(f"Successfully canceled subscription {user_subscription.polar_subscription_id} for user {request.user.email}")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Failed to cancel subscription: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except UserSubscription.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No active subscription found.'}, status=404)