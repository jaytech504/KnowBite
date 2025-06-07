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
    try:
        sub = UserSubscription.objects.get(user=request.user)
    except UserSubscription.DoesNotExist:
        sub = None
    return render(request, 'knowbite/subscription_status.html', {'subscription': sub})

@csrf_exempt
def paddle_webhook(request):
    try:
        payload = json.loads(request.body)
        event_type = payload.get('event_type')
        data = payload.get('data', {})
        
        # Get user subscription
        subscription_id = data.get('subscription_id')
        try:
            user_sub = UserSubscription.objects.get(paddle_subscription_id=subscription_id)
        except UserSubscription.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Subscription not found'}, status=404)

        # Update last webhook timestamp
        user_sub.last_webhook_received = timezone.now()
        
        if event_type == 'subscription.created':
            # New subscription created
            user_sub.status = 'trialing' if data.get('trial_end') else 'active'
            user_sub.is_active = True
            user_sub.trial_end = parse_iso_date(data.get('trial_end'))
            user_sub.current_period_start = parse_iso_date(data.get('current_period_start'))
            user_sub.current_period_end = parse_iso_date(data.get('current_period_end'))
            
        elif event_type == 'subscription.updated':
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
        
        # Send email notifications based on event type
        send_subscription_notification(user_sub, event_type)
        
        return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
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