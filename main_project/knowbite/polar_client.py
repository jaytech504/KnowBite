from django.conf import settings
from polar_sdk import Polar, PolarError
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PolarClient:
    def __init__(self):
        self.client = Polar(
            access_token=settings.POLAR_API_KEY  # Correct initialization
        )

    def create_checkout_session(self, user_email: str, plan_id: str) -> Optional[str]:
        """Create a Polar checkout session"""
        try:
            checkout = self.client.checkouts.create(
                success_url="https://knowbite.onrender.com/subscription-success",
                cancel_url="https://knowbite.onrender.com/pricing",
                email=user_email,
                plan_id=plan_id
            )
            return checkout.url
        except PolarError as e:
            logger.error(f"Error creating Polar checkout session: {str(e)}")
            return None

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription in Polar"""
        try:
            self.client.subscriptions.cancel(subscription_id=subscription_id)
            return True
        except PolarError as e:
            logger.error(f"Error canceling Polar subscription: {str(e)}")
            return False

    def verify_webhook(self, payload: dict, signature: str) -> bool:
        """Verify webhook signature"""
        try:
            return self.client.webhooks.verify_signature(
                payload=payload,
                signature=signature,
                secret=settings.POLAR_WEBHOOK_SECRET
            )
        except Exception as e:
            logger.error(f"Error verifying webhook: {str(e)}")
            return False
