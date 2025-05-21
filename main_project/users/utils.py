from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from datetime import datetime

def send_welcome_email(user):
    subject = "Welcome to MyApp!"
    message = render_to_string('users/welcome_email.html', {
        'user': user,
        'current_year': datetime.now().year
    })
    send_mail(
        subject,
        '',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=message
    )

def send_login_notification(user, request=None):
    subject = "Login Alert"
    message = render_to_string('users/login_notification.html', {
        'user': user,
        'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'ip_address': get_client_ip(request),
        'current_year': datetime.now().year
    })
    send_mail(
        subject,
        '',
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=message
    )

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
