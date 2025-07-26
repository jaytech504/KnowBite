from django.contrib.auth.signals import user_logged_in
from allauth.account.signals import user_signed_up
from django.dispatch import receiver
from users.utils import send_login_notification, send_welcome_email

@receiver(user_logged_in)
def send_login_email(sender, request, user, **kwargs):
    send_login_notification(user)  # Reusable function

@receiver(user_signed_up)
def send_signup_email(sender, request, user, **kwargs):
    send_welcome_email(user)