"""
payments.py (root) — DEPRECATED.

This file previously contained a Stripe implementation that conflicts with
the Razorpay implementation in backend/payments.py.

All payment logic now lives exclusively in backend/payments.py (Razorpay).
This file is kept only so existing imports don't crash; it re-exports
everything from the canonical module.

TO DO: Delete this file once you've confirmed no external scripts reference it.
"""
from backend.payments import (   # noqa: F401  (re-export everything)
    router,
    create_order,
    verify_payment_signature,
    upgrade_user_tier,
    use_credits,
)
