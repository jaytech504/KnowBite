from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from .models import Plan, UserSubscription
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
import datetime

@login_required
def pricing(request):
    plans = Plan.objects.all().order_by('price')
    return render(request, 'knowbite/pricing.html', {
        'plans': plans,
        'paddle_vendor_id': settings.PADDLE_VENDOR_ID,
        'paddle_sandbox': settings.PADDLE_SANDBOX,
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
    # Paddle will POST subscription events here
    if request.method == 'POST':
        data = request.POST.dict()
        alert_name = data.get('alert_name')
        user_email = data.get('email')
        paddle_subscription_id = data.get('subscription_id')
        plan_id = data.get('subscription_plan_id')
        status = data.get('status', 'active')
        next_bill_date = data.get('next_bill_date')

        # Find user by email
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return HttpResponse('User not found', status=404)

        # Find the plan
        try:
            plan = Plan.objects.get(paddle_plan_id=plan_id)
        except Plan.DoesNotExist:
            return HttpResponse('Plan not found', status=404)

        # Create or update subscription
        sub, created = UserSubscription.objects.get_or_create(user=user)
        sub.paddle_subscription_id = paddle_subscription_id
        sub.plan = plan
        sub.is_active = (status == 'active')
        if next_bill_date:
            try:
                sub.current_period_end = datetime.datetime.strptime(next_bill_date, "%Y-%m-%d")
            except Exception:
                sub.current_period_end = None
        sub.save()
        return HttpResponse('OK')
    return HttpResponse('Invalid', status=400)