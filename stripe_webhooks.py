"""
Stripe Webhook Handler for FINXPLORER Subscription Events

⚠️  DEPRECATED: This module is deprecated and will be removed in a future version.
    Please use `fh_saas.utils_stripe` instead:
    
    ```python
    from fh_saas.utils_stripe import (
        StripeService,
        StripeConfig,
        get_stripe_service,
        create_webhook_route,
    )
    
    # Initialize service
    service = get_stripe_service()
    
    # Create webhook route (FastHTML)
    create_webhook_route(app, service)
    
    # Or handle manually:
    event = service.verify_signature(payload, sig_header)
    result = service.handle_event(event)
    ```

Handles Stripe webhook events for subscription lifecycle management including:
- checkout.session.completed: New subscription creation from checkout
- customer.subscription.created: Subscription initialization
- customer.subscription.updated: Plan changes, trial ending, status updates
- customer.subscription.deleted: Subscription cancellation
- invoice.payment_succeeded: Successful subscription renewal
- invoice.payment_failed: Failed payment handling

Uses SqlUtil for database operations and queries.json for SQL queries.
"""

import warnings
warnings.warn(
    "stripe_webhooks module is deprecated. Use fh_saas.utils_stripe instead.",
    DeprecationWarning,
    stacklevel=2
)

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

import stripe
from dotenv import load_dotenv

from utils.sql_util import SqlUtil
from services.tenant.tenant_db_service import get_tenant_db_service
from utils.config import get_config

load_dotenv()
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv("CONFIG_STRIPE_SECRETKEY")
STRIPE_WEBHOOK_SECRET = os.getenv("CONFIG_STRIPE_WEBHOOKSECRET")

# Get environment config
config = get_config()
IS_DEVELOPMENT = config.environment == "development"


class StripeWebhookHandler:
    """Handles Stripe webhook events for subscription management"""
    
    def __init__(self):
        self.tenant_service = get_tenant_db_service()
        self.host_db = self.tenant_service.get_host_database()
        self.sql_util = SqlUtil(self.host_db)
    
    def verify_signature(self, payload: bytes, sig_header: str) -> Optional[Dict[str, Any]]:
        """
        Verify Stripe webhook signature and return event
        
        In development mode: Skip signature verification if webhook secret is not configured
        In production mode: Always require valid signature
        """
        # Development mode: Skip verification if not configured
        if IS_DEVELOPMENT and (not STRIPE_WEBHOOK_SECRET or not sig_header):
            logger.warning("⚠️  DEVELOPMENT MODE: Skipping Stripe webhook signature verification")
            try:
                # Parse payload as JSON event
                event = json.loads(payload.decode('utf-8'))
                return event
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.error(f"Invalid webhook payload in dev mode: {e}")
                return None
        
        # Production mode or dev mode with proper config: Verify signature
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
            return event
        except ValueError as e:
            logger.error(f"Invalid webhook payload: {e}")
            return None
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            return None
    
    def handle_event(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Route webhook event to appropriate handler"""
        event_type = event.get("type")
        
        handlers = {
            "checkout.session.completed": self.handle_checkout_completed,
            "customer.subscription.created": self.handle_subscription_created,
            "customer.subscription.updated": self.handle_subscription_updated,
            "customer.subscription.deleted": self.handle_subscription_deleted,
            "invoice.payment_succeeded": self.handle_payment_succeeded,
            "invoice.payment_failed": self.handle_payment_failed,
        }
        
        handler = handlers.get(event_type)
        if handler:
            try:
                return handler(event)
            except Exception as e:
                logger.error(f"Error handling {event_type}: {e}")
                traceback.print_exc()
                return {"status": "error", "message": str(e)}
        else:
            logger.info(f"Unhandled event type: {event_type}")
            return {"status": "ignored", "message": f"Event type {event_type} not handled"}
    
    def handle_checkout_completed(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle successful checkout session completion"""
        session = event["data"]["object"]
        
        # Extract metadata from checkout session
        metadata = session.get("metadata", {})
        tenant_id = metadata.get("tenant_id")
        user_email = metadata.get("user_email")
        plan_type = metadata.get("plan_type", "monthly")
        
        if not tenant_id or not user_email:
            logger.error(f"Missing required metadata in checkout session: {session['id']}")
            return {"status": "error", "message": "Missing tenant_id or user_email"}
        
        # Get subscription details from Stripe
        stripe_subscription_id = session.get("subscription")
        stripe_customer_id = session.get("customer")
        checkout_session_id = session["id"]
        
        if stripe_subscription_id:
            # Fetch full subscription details from Stripe
            subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            
            # Create subscription record in database
            self._upsert_subscription(
                tenant_id=tenant_id,
                user_email=user_email,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=stripe_customer_id,
                stripe_checkout_session_id=checkout_session_id,
                plan_type=plan_type,
                subscription=subscription
            )
            
            # Update user's stripe_customer_id in host database
            self._update_user_stripe_customer(user_email, stripe_customer_id)
            
            logger.info(f"Subscription created for tenant {tenant_id}: {stripe_subscription_id}")
            return {"status": "success", "message": "Subscription created"}
        else:
            logger.warning(f"No subscription ID in checkout session: {checkout_session_id}")
            return {"status": "warning", "message": "No subscription found in session"}
    
    def handle_subscription_created(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription creation (triggered after checkout)"""
        subscription = event["data"]["object"]
        
        # Extract metadata (set during checkout)
        metadata = subscription.get("metadata", {})
        tenant_id = metadata.get("tenant_id")
        user_email = metadata.get("user_email")
        plan_type = metadata.get("plan_type", "monthly")
        
        if tenant_id and user_email:
            self._upsert_subscription(
                tenant_id=tenant_id,
                user_email=user_email,
                stripe_subscription_id=subscription["id"],
                stripe_customer_id=subscription["customer"],
                plan_type=plan_type,
                subscription=subscription
            )
            logger.info(f"Subscription initialized for tenant {tenant_id}")
            return {"status": "success", "message": "Subscription initialized"}
        else:
            logger.warning(f"Subscription created without metadata: {subscription['id']}")
            return {"status": "warning", "message": "Subscription created but missing metadata"}
    
    def handle_subscription_updated(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription updates (status changes, plan changes, etc.)"""
        subscription = event["data"]["object"]
        stripe_subscription_id = subscription["id"]
        
        # Find existing subscription record
        existing = self._find_subscription_by_stripe_id(stripe_subscription_id)
        
        if existing:
            tenant_id = existing["tenant_id"]
            user_email = existing["user_email"]
            plan_type = existing["plan_type"]
            
            # Update subscription record
            self._upsert_subscription(
                tenant_id=tenant_id,
                user_email=user_email,
                stripe_subscription_id=stripe_subscription_id,
                stripe_customer_id=subscription["customer"],
                plan_type=plan_type,
                subscription=subscription
            )
            
            logger.info(f"Subscription updated for tenant {tenant_id}: {stripe_subscription_id}")
            return {"status": "success", "message": "Subscription updated"}
        else:
            logger.warning(f"Subscription update for unknown subscription: {stripe_subscription_id}")
            return {"status": "warning", "message": "Subscription not found in database"}
    
    def handle_subscription_deleted(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle subscription cancellation"""
        subscription = event["data"]["object"]
        stripe_subscription_id = subscription["id"]
        
        # Mark subscription as canceled in database
        try:
            updated_at = datetime.utcnow().isoformat()
            canceled_at = datetime.utcnow().isoformat()
            
            self.sql_util.execute_query(
                query_id="subscription_cancel",
                params={
                    "stripe_subscription_id": stripe_subscription_id,
                    "cancel_at_period_end": subscription.get("cancel_at_period_end", False),
                    "canceled_at": canceled_at,
                    "updated_at": updated_at,
                }
            )
            
            logger.info(f"Subscription canceled: {stripe_subscription_id}")
            return {"status": "success", "message": "Subscription canceled"}
        except Exception as e:
            logger.error(f"Error canceling subscription {stripe_subscription_id}: {e}")
            return {"status": "error", "message": str(e)}
    
    def handle_payment_succeeded(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle successful subscription payment"""
        invoice = event["data"]["object"]
        stripe_subscription_id = invoice.get("subscription")
        
        if stripe_subscription_id:
            # Ensure subscription status is 'active' in database
            try:
                updated_at = datetime.utcnow().isoformat()
                
                self.sql_util.execute_query(
                    query_id="subscription_update_status",
                    params={
                        "stripe_subscription_id": stripe_subscription_id,
                        "status": "active",
                        "updated_at": updated_at,
                    }
                )
                
                logger.info(f"Payment succeeded for subscription: {stripe_subscription_id}")
                return {"status": "success", "message": "Payment recorded"}
            except Exception as e:
                logger.error(f"Error updating payment status: {e}")
                return {"status": "error", "message": str(e)}
        else:
            logger.info(f"Payment succeeded for invoice without subscription: {invoice['id']}")
            return {"status": "success", "message": "Payment recorded (no subscription)"}
    
    def handle_payment_failed(self, event: Dict[str, Any]) -> Dict[str, str]:
        """Handle failed subscription payment"""
        invoice = event["data"]["object"]
        stripe_subscription_id = invoice.get("subscription")
        
        if stripe_subscription_id:
            # Update subscription status to 'past_due'
            try:
                updated_at = datetime.utcnow().isoformat()
                
                self.sql_util.execute_query(
                    query_id="subscription_update_status",
                    params={
                        "stripe_subscription_id": stripe_subscription_id,
                        "status": "past_due",
                        "updated_at": updated_at,
                    }
                )
                
                logger.warning(f"Payment failed for subscription: {stripe_subscription_id}")
                return {"status": "success", "message": "Payment failure recorded"}
            except Exception as e:
                logger.error(f"Error updating payment failure: {e}")
                return {"status": "error", "message": str(e)}
        else:
            logger.warning(f"Payment failed for invoice without subscription: {invoice['id']}")
            return {"status": "success", "message": "Payment failure recorded (no subscription)"}
    
    def _upsert_subscription(
        self,
        tenant_id: str,
        user_email: str,
        stripe_subscription_id: str,
        stripe_customer_id: str,
        plan_type: str,
        subscription: Dict[str, Any],
        stripe_checkout_session_id: str = None
    ) -> None:
        """Upsert subscription record in database"""
        
        # Generate unique subscription_id if not exists
        existing = self._find_subscription_by_stripe_id(stripe_subscription_id)
        subscription_id = existing["subscription_id"] if existing else f"sub_{stripe_subscription_id}"
        
        # Extract subscription details
        status = subscription.get("status", "incomplete")
        trial_start = self._timestamp_to_iso(subscription.get("trial_start"))
        trial_end = self._timestamp_to_iso(subscription.get("trial_end"))
        current_period_start = self._timestamp_to_iso(subscription.get("current_period_start"))
        current_period_end = self._timestamp_to_iso(subscription.get("current_period_end"))
        cancel_at_period_end = subscription.get("cancel_at_period_end", False)
        canceled_at = self._timestamp_to_iso(subscription.get("canceled_at"))
        created_at = self._timestamp_to_iso(subscription.get("created")) or datetime.utcnow().isoformat()
        updated_at = datetime.utcnow().isoformat()
        
        # Prepare metadata (store additional Stripe data)
        metadata = json.dumps({
            "stripe_metadata": subscription.get("metadata", {}),
            "plan_id": subscription.get("plan", {}).get("id"),
            "billing_cycle_anchor": subscription.get("billing_cycle_anchor"),
        })
        
        # Upsert subscription record
        self.sql_util.execute_query(
            query_id="subscription_upsert",
            params={
                "subscription_id": subscription_id,
                "tenant_id": tenant_id,
                "user_email": user_email,
                "stripe_subscription_id": stripe_subscription_id,
                "stripe_customer_id": stripe_customer_id,
                "stripe_checkout_session_id": stripe_checkout_session_id,
                "plan_type": plan_type,
                "status": status,
                "trial_start": trial_start,
                "trial_end": trial_end,
                "current_period_start": current_period_start,
                "current_period_end": current_period_end,
                "cancel_at_period_end": cancel_at_period_end,
                "canceled_at": canceled_at,
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": metadata,
            }
        )
    
    def _find_subscription_by_stripe_id(self, stripe_subscription_id: str) -> Optional[Dict[str, Any]]:
        """Find subscription record by Stripe subscription ID"""
        try:
            result = self.sql_util.execute_query(
                query_id="subscription_find_by_stripe_id",
                params={"stripe_subscription_id": stripe_subscription_id},
                fetch_one=True
            )
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Error finding subscription {stripe_subscription_id}: {e}")
            return None
    
    def _update_user_stripe_customer(self, user_email: str, stripe_customer_id: str) -> None:
        """Update user's Stripe customer ID in host database"""
        try:
            # Use raw SQL update since user table is in host database
            from sqlalchemy import text
            
            query = text("""
                UPDATE "user" 
                SET stripe_customer_id = :stripe_customer_id 
                WHERE email = :email
            """)
            
            self.host_db.conn.execute(query, {
                "stripe_customer_id": stripe_customer_id,
                "email": user_email
            })
            self.host_db.conn.commit()
            
            logger.info(f"Updated Stripe customer ID for user {user_email}")
        except Exception as e:
            logger.error(f"Error updating user Stripe customer ID: {e}")
    
    @staticmethod
    def _timestamp_to_iso(timestamp: Optional[int]) -> Optional[str]:
        """Convert Unix timestamp to ISO format string"""
        if timestamp:
            return datetime.utcfromtimestamp(timestamp).isoformat()
        return None


def get_stripe_webhook_handler() -> StripeWebhookHandler:
    """Factory function for StripeWebhookHandler singleton"""
    global _stripe_webhook_handler
    if '_stripe_webhook_handler' not in globals():
        _stripe_webhook_handler = StripeWebhookHandler()
    return _stripe_webhook_handler
