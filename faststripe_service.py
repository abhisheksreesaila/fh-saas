"""
FastStripe Service for FINXPLORER Subscription Management

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.
    Please use `fh_saas.utils_stripe` instead:
    
    ```python
    from fh_saas.utils_stripe import (
        StripeService,
        StripeConfig,
        get_stripe_service,
        create_subscription_checkout,
    )
    
    # Initialize service
    service = get_stripe_service()
    
    # Create checkout
    checkout = service.create_subscription_checkout(
        plan_type='monthly',
        tenant_id='tnt_123',
        user_email='user@example.com'
    )
    ```

Handles subscription checkout with 30-day free trial for both monthly and yearly plans.
Uses FastStripe wrapper around Stripe API for simplified subscription management.
"""

import warnings
warnings.warn(
    "faststripe_service module is deprecated. Use fh_saas.utils_stripe instead.",
    DeprecationWarning,
    stacklevel=2
)

from faststripe.core import StripeApi
import os
from dotenv import load_dotenv

class FastStripeService:
    """Service for managing FastStripe subscription checkouts"""
    
    def __init__(self):
        load_dotenv()
        self.sapi = StripeApi(os.environ['CONFIG_STRIPE_SECRETKEY'])
        self.trial_days = 30
        self.base_url = os.getenv('BASE_URL', 'http://localhost:5001')
        
    def create_monthly_subscription(self, customer_email: str = None):
        """
        Create monthly subscription checkout with 30-day trial
        
        Args:
            customer_email: Optional pre-fill customer email
            
        Returns:
            Stripe Checkout Session object with url and id
        """
        try:
            # Create product first
            product = self.sapi.products.post(
                name='FINXPLORER Monthly Plan',
                description='Unlimited transaction tracking, budget management, bank connections, financial insights & reports'
            )
            
            # Create recurring price
            price = self.sapi.prices.post(
                product=product.id,
                unit_amount=799,  # $7.99 in cents
                currency='usd',
                recurring={'interval': 'month'}
            )
            
            # Create checkout session with trial
            checkout_params = {
                'mode': 'subscription',
                'line_items': [{
                    'price': price.id,
                    'quantity': 1
                }],
                'success_url': f'{self.base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}',
                'cancel_url': f'{self.base_url}/settings/payment',
                'subscription_data': {
                    'trial_period_days': self.trial_days,
                    'metadata': {
                        'plan_type': 'monthly',
                        'service': 'finxplorer'
                    }
                },
                'allow_promotion_codes': True
            }
            
            if customer_email:
                checkout_params['customer_email'] = customer_email
            
            checkout = self.sapi.checkout.sessions_post(**checkout_params)
            return checkout
            
        except Exception as e:
            print(f"Error creating monthly subscription: {e}")
            raise
        
    def create_yearly_subscription(self, customer_email: str = None):
        """
        Create yearly subscription checkout with 30-day trial
        
        Args:
            customer_email: Optional pre-fill customer email
            
        Returns:
            Stripe Checkout Session object with url and id
        """
        try:
            # Create product first
            product = self.sapi.products.post(
                name='FINXPLORER Yearly Plan',
                description='All monthly features + advanced analytics, forecasting, custom categories, exports, priority support, mobile app'
            )
            
            # Create recurring price
            price = self.sapi.prices.post(
                product=product.id,
                unit_amount=7900,  # $79.00 in cents
                currency='usd',
                recurring={'interval': 'year'}
            )
            
            # Create checkout session with trial
            checkout_params = {
                'mode': 'subscription',
                'line_items': [{
                    'price': price.id,
                    'quantity': 1
                }],
                'success_url': f'{self.base_url}/payment-success?session_id={{CHECKOUT_SESSION_ID}}',
                'cancel_url': f'{self.base_url}/settings/payment',
                'subscription_data': {
                    'trial_period_days': self.trial_days,
                    'metadata': {
                        'plan_type': 'yearly',
                        'service': 'finxplorer'
                    }
                },
                'allow_promotion_codes': True
            }
            
            if customer_email:
                checkout_params['customer_email'] = customer_email
            
            checkout = self.sapi.checkout.sessions_post(**checkout_params)
            return checkout
            
        except Exception as e:
            print(f"Error creating yearly subscription: {e}")
            raise
    
    def get_subscription(self, subscription_id: str):
        """Retrieve subscription details from Stripe"""
        try:
            return self.sapi.subscriptions.get(subscription_id)
        except Exception as e:
            print(f"Error retrieving subscription {subscription_id}: {e}")
            raise
    
    def cancel_subscription(self, subscription_id: str):
        """Cancel a subscription at period end"""
        try:
            return self.sapi.subscriptions.delete(subscription_id)
        except Exception as e:
            print(f"Error canceling subscription {subscription_id}: {e}")
            raise

# Singleton factory pattern following FINXPLORER conventions
_faststripe_service = None

def get_faststripe_service() -> FastStripeService:
    """
    Get or create singleton FastStripe service instance
    
    Returns:
        FastStripeService instance
    """
    global _faststripe_service
    if _faststripe_service is None:
        _faststripe_service = FastStripeService()
    return _faststripe_service
