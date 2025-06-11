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

logger = logging.getLogger(__name__)

def create_or_update_subscription(user, subscription_id, plan, trial_end=None, 
                                current_period_start=None, current_period_end=None):
    """Helper function to create or update a user subscription"""
    try:
        subscription, created = UserSubscription.objects.update_or_create(
            user=user,
            defaults={
                'paddle_subscription_id': subscription_id,
                'plan': plan,
                'status': 'trialing' if trial_end else 'active',
                'is_active': True,
                'trial_end': trial_end,
                'current_period_start': current_period_start,
                'current_period_end': current_period_end,
                'last_webhook_received': timezone.now()
            }
        )
        logger.info(f"{'Created' if created else 'Updated'} subscription for user {user.email}")
        return subscription
    except Exception as e:
        logger.error(f"Error creating/updating subscription for user {user.email}: {str(e)}")
        return None

@login_required
def pricing(request):
    plans = Plan.objects.all().order_by('price')    
    return render(request, 'knowbite/pricing.html', {
        'plans': plans,
        'paddle_vendor_id': settings.PADDLE_VENDOR_ID,
        'paddle_sandbox': settings.PADDLE_SANDBOX,
        'paddle_client_token': settings.PADDLE_CLIENT_TOKEN,
    })

@login_required
def subscription_status(request):
    """View to display subscription status"""
    try:
        user_subscription = UserSubscription.objects.get(user=request.user)
        logger.info(f"Found subscription for user {request.user.email}: {user_subscription.status}")
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
            'paddle_subscription_id': subscription.paddle_subscription_id
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

import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def paddle_webhook(request):
    try:
        payload = json.loads(request.body)
        event_type = payload.get('event_type')
        data = payload.get('data', {})
        
        logger.info(f"Received webhook event: {event_type}")
        logger.debug(f"Webhook payload: {payload}")
        
        subscription_id = data.get('subscription_id')
        
        if event_type == 'subscription.created':
            custom_data = data.get('custom_data', {})
            user_id = custom_data.get('user_id')
            logger.info(f"Webhook custom_data: {custom_data}")
            if not user_id:
                logger.error("No user_id in custom_data!")
                return JsonResponse({'status': 'error', 'message': 'No user_id in custom_data'}, status=400)
            try:
                user = User.objects.get(id=user_id)
                logger.info(f"Found user for webhook: {user}")
            except User.DoesNotExist:
                logger.error(f"User with id {user_id} not found!")
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            price_id = data.get('items', [{}])[0].get('price', {}).get('id')
            logger.info(f"Webhook price_id: {price_id}")
            try:
                plan = Plan.objects.get(paddle_plan_id=price_id)
                logger.info(f"Found plan for webhook: {plan}")
            except Plan.DoesNotExist:
                logger.error(f"Plan with paddle_plan_id {price_id} not found!")
                return JsonResponse({'status': 'error', 'message': 'Plan not found'}, status=404)
            subscription = create_or_update_subscription(
                user=user,
                subscription_id=subscription_id,
                plan=plan,
                trial_end=parse_iso_date(data.get('trial_end')),
                current_period_start=parse_iso_date(data.get('current_period_start')),
                current_period_end=parse_iso_date(data.get('current_period_end')),
            )
            if subscription:
                logger.info(f"Subscription created/updated: {subscription}")
            else:
                logger.error("Failed to create/update subscription!")
            return JsonResponse({'status': 'success'})
        
        # If not subscription.created, try to find existing subscription
        try:
            user_sub = UserSubscription.objects.get(paddle_subscription_id=subscription_id)
        except UserSubscription.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Subscription not found'}, status=404)

        # Update last webhook timestamp
        user_sub.last_webhook_received = timezone.now()
        
        if event_type == 'subscription.updated':
            # Subscription details updated
            user_sub.current_period_start = parse_iso_date(data.get('current_period_start'))
            user_sub.current_period_end = parse_iso_date(data.get('current_period_end'))
            if data.get('status'):
                user_sub.status = data['status']
            user_sub.is_active = data.get('status') in ['trialing', 'active']
            
        elif event_type == 'subscription.canceled':
            # Subscription canceled
            user_sub.status = 'canceled'
            user_sub.is_active = False
            user_sub.canceled_at = timezone.now()
            
        elif event_type == 'subscription.trial_ended':
            # Trial period ended
            user_sub.status = 'active'
            user_sub.trial_end = timezone.now()
            
        user_sub.save()
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

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