from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from users.utils import send_login_notification

@receiver(user_logged_in)
def send_login_email(sender, request, user, **kwargs):
    send_login_notification(user)  # Reusable function