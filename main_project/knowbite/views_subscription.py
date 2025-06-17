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
import requests

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
    user_subscription = UserSubscription.objects.get(user=request.user)
    
    return render(request, 'knowbite/pricing.html', {
        'plans': plans,
        'current_plan': user_subscription.plan,
        'paddle_vendor_id': settings.PADDLE_VENDOR_ID,
        'paddle_sandbox': settings.PADDLE_SANDBOX,
        'paddle_client_token': settings.PADDLE_CLIENT_TOKEN,
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
                user_subscription.paddle_subscription_id = None
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
    """
    Handle Paddle webhook notifications
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed'}, status=405)

    # Log raw request details for debugging
    logger.info('=== Paddle Webhook Received ===')
    logger.info(f'Request Method: {request.method}')
    logger.info(f'Content Type: {request.content_type}')
    logger.info(f'Headers: {dict(request.headers)}')
    logger.info(f'Body: {request.body.decode("utf-8")}')

    try:
        payload = json.loads(request.body)
        event_type = payload.get('event_type')
        data = payload.get('data', {})
        print('--- Paddle Webhook Received ---')
        print('Event:', event_type)
        print('Payload:', json.dumps(payload, indent=2))
        logger.info(f"Received webhook event: {event_type}")
        logger.info(f"Full webhook payload: {json.dumps(payload, indent=2)}")
        
        # Debug information about the request
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type if hasattr(request, 'content_type') else 'Not set'}")
        
        # Print the actual data structure we're working with
        logger.info(f"Custom data: {data.get('custom_data', {})}")
        logger.info(f"Items data: {data.get('items', [])}")
        logger.info(f"Subscription ID: {data.get('subscription_id')}")
        
        if event_type in ['subscription.created', 'transaction.completed', 'transaction.paid']:
            # Get price ID from items
            items = data.get('items', [])
            price_id = None
            if items and len(items) > 0:
                price = items[0].get('price', {})
                price_id = price.get('id') if isinstance(price, dict) else None
                logger.info(f"Found price_id: {price_id}")
            else:
                logger.warning("No items found in webhook data")
        
        subscription_id = data.get('subscription_id')
          # Get common data from webhook
        custom_data = data.get('custom_data', {})
        user_id = custom_data.get('user_id')
        
        if event_type in ['subscription.created', 'transaction.completed', 'transaction.paid']:
            # These events create or update subscriptions
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            
            # Get the plan from the price_id
            price_id = data.get('items', [{}])[0].get('price', {}).get('id')
            try:
                plan = Plan.objects.get(paddle_plan_id=price_id)
            except Plan.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Plan not found'}, status=404)
            
            # Create or update subscription
            defaults = {
                'plan': plan,
                'status': 'trialing' if data.get('trial_end') else 'active',
                'is_active': True,
                'last_webhook_received': timezone.now()
            }
            
            # Add subscription_id if available            if subscription_id:
            defaults['paddle_subscription_id'] = subscription_id
            
            # Add dates if available
            if data.get('trial_end'):
                defaults['trial_end'] = parse_iso_date(data.get('trial_end'))
            if data.get('billing_period'):
                period = data.get('billing_period', {})
                defaults['current_period_start'] = parse_iso_date(period.get('starts_at'))
                defaults['current_period_end'] = parse_iso_date(period.get('ends_at'))
            else:
                defaults['current_period_start'] = parse_iso_date(data.get('current_period_start'))
                defaults['current_period_end'] = parse_iso_date(data.get('current_period_end'))
            
            # Get the existing subscription if any
            try:
                existing_sub = UserSubscription.objects.get(user=user)
                # Update the existing subscription
                for key, value in defaults.items():
                    setattr(existing_sub, key, value)
                existing_sub.plan = plan  # Explicitly set the plan
                existing_sub.save()
                subscription = existing_sub
                created = False
                logger.info(f"Updated existing subscription for user {user.email} to plan {plan.name}")
            except UserSubscription.DoesNotExist:
                # Create new subscription
                subscription = UserSubscription.objects.create(
                    user=user,
                    plan=plan,
                    **defaults
                )
                created = True
                logger.info(f"Created new subscription for user {user.email} with plan {plan.name}")
            logger.info(f"Created/Updated subscription for {event_type}: user={user.email}, plan={plan}, subscription_id={subscription_id}")
            return JsonResponse({'status': 'success'})
        
        # For events that update existing subscriptions, find the subscription
        if subscription_id:
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
            
        elif event_type == 'transaction.updated':
            # Get user from custom_data
            custom_data = data.get('custom_data', {})
            user_id = custom_data.get('user_id')
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            # Find or create UserSubscription
            user_sub, _ = UserSubscription.objects.get_or_create(user=user)
            # Set paddle_subscription_id if not set
            if not user_sub.paddle_subscription_id and data.get('subscription_id'):
                user_sub.paddle_subscription_id = data['subscription_id']
            # Update other fields as needed
            user_sub.status = 'active' if data.get('status') == 'completed' else data.get('status', user_sub.status)
            user_sub.is_active = user_sub.status in ['trialing', 'active']
            period = data.get('billing_period', {})
            user_sub.current_period_start = parse_iso_date(period.get('starts_at'))
            user_sub.current_period_end = parse_iso_date(period.get('ends_at'))
            user_sub.last_webhook_received = timezone.now()
            user_sub.save()
            return JsonResponse({'status': 'success'})
        
        elif event_type == 'transaction.paid':
            # Handle transaction.paid event (no subscription_id, but has user info and price_id)
            custom_data = data.get('custom_data', {})
            user_id = custom_data.get('user_id')
            price_id = None
            items = data.get('items', [])
            if items and 'price' in items[0]:
                price_id = items[0]['price'].get('id')
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
            try:
                plan = Plan.objects.get(paddle_plan_id=price_id)
            except Plan.DoesNotExist:
                plan = None
            # Create or update subscription (no paddle_subscription_id yet)
            subscription, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'status': 'active',
                    'is_active': True,
                    'last_webhook_received': timezone.now()
                }
            )
            logger.info(f"Handled transaction.paid for user {user.email}, plan {plan}, created={created}")
            return JsonResponse({'status': 'success'})
        
        elif event_type == 'transaction.completed':
            # Handle transaction.completed event
            custom_data = data.get('custom_data', {})
            user_id = custom_data.get('user_id')
            subscription_id = data.get('subscription_id')
            price_id = None
            items = data.get('items', [])
            if items and 'price' in items[0]:
                price_id = items[0]['price'].get('id')

            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)

            try:
                plan = Plan.objects.get(paddle_plan_id=price_id)
            except Plan.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Plan not found'}, status=404)

            # Get billing period info
            billing_period = data.get('billing_period', {})
            period_start = parse_iso_date(billing_period.get('starts_at'))
            period_end = parse_iso_date(billing_period.get('ends_at'))

            # Create or update subscription
            subscription, created = UserSubscription.objects.update_or_create(
                user=user,
                defaults={
                    'paddle_subscription_id': subscription_id,
                    'plan': plan,
                    'status': 'active',
                    'is_active': True,
                    'current_period_start': period_start,
                    'current_period_end': period_end,
                    'last_webhook_received': timezone.now()
                }
            )
            logger.info(f"Handled transaction.completed for user {user.email}, plan {plan}, subscription_id {subscription_id}")
            return JsonResponse({'status': 'success'})
        
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # If event type was not handled above, return a generic response
    return JsonResponse({'status': 'ignored', 'message': f'Unhandled event type: {event_type}'})

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
        if not user_subscription.paddle_subscription_id:
            return JsonResponse({'status': 'error', 'message': 'No Paddle subscription ID found.'}, status=400)

        # Paddle API endpoint
        if getattr(settings, 'PADDLE_SANDBOX', False):
            paddle_api_url = 'https://sandbox-api.paddle.com/subscriptions/'
        else:
            paddle_api_url = 'https://api.paddle.com/subscriptions/'
        cancel_url = f"{paddle_api_url}{user_subscription.paddle_subscription_id}/cancel"

        headers = {
            'Authorization': f'Bearer {settings.PADDLE_API_KEY}',
            'Content-Type': 'application/json',
        }        
        try:
            response = requests.post(cancel_url, headers=headers)
            response_data = response.json() if response.text else {}
            
            if response.status_code in (200, 204):
                user_subscription.status = 'canceled'
                user_subscription.is_active = False
                user_subscription.canceled_at = timezone.now()
                user_subscription.save()
                logger.info(f"Successfully canceled subscription {user_subscription.paddle_subscription_id} for user {request.user.email}")
                return JsonResponse({'status': 'success'})
            else:
                error_message = response_data.get('error', {}).get('message', response.text)
                logger.error(f"Failed to cancel subscription: {error_message}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Paddle API error: {error_message}',
                    'code': response.status_code
                }, status=400)
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error canceling subscription: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Network error while contacting Paddle API'
            }, status=500)
    except UserSubscription.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'No active subscription found.'}, status=404)