from django.conf import settings
import resend

resend.api_key = settings.RESEND_API_KEY
def send_welcome_email(user):
    resend.Emails.send({
        "from": "Knowbite <onboarding@resend.dev>",
        "to": [user.email],
        "subject": "🎉Welcome to KnowBite",
        "html": f"""<h2>Welcome { user.username }!</h2>
                <p>Thanks for signing up at <strong>KnowBite</strong>.</p>
                <p>We are excited to have you onboard.</p>"""
    })

def send_login_notification(user):
    resend.Emails.send({
        "from": "Knowbite <onboarding@resend.dev>",
        "to": [user.email],
        "subject": "🎉Login alert from KnowBite",
        "html": f"""<h2>Hey { user.username }!</h2>
                <p>You logged into your account at <strong>KnowBite</strong>.</p>
                <p>We are excited to have you back.</p>"""
    })