from django.core.mail import send_mail
from django.conf import settings


def send_welcome_email(user):
    subject = "🎉 Welcome to Our Platform!"
    message = f"Hello {user.username},\n\nThank you for registering with us. We're excited to have you on board!"
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )


def send_login_notification(user):
    subject = "Welcome to Our Platform"
    message = f"Hi {user.username},\n\nThank you for registering on our platform!"
    from_email = None  # Will use DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list)