"""
app/services/safepay_service.py
Service helper for Safepay Order API v1 integration.
Official documentation: https://docs.getsafepay.com / Order API v1 (POST /order/v1/init)
Safepay Order API v1 expects and returns amount in major currency units (PKR Rupees).
"""

import logging
import requests as http_requests
from flask import current_app

logger = logging.getLogger(__name__)

SAFEPAY_HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
}


def to_safepay_amount(amount) -> float:
    """
    Convert internal appointment fee (in PKR Rupees) to Safepay Order API v1 format.
    Safepay's /order/v1/init endpoint expects major units (Rupees, e.g. 2500.00).
    """
    if amount is None:
        raise ValueError("Amount cannot be None")
    return round(float(amount), 2)


def from_safepay_amount(safepay_amount) -> float:
    """
    Convert Safepay Order API v1 returned amount to internal appointment fee format (PKR Rupees).
    Safepay's /order/v1/{token} returns major units (Rupees).
    """
    if safepay_amount is None:
        raise ValueError("Safepay amount cannot be None")
    if isinstance(safepay_amount, dict):
        safepay_amount = safepay_amount.get('amount', 0)
    return round(float(safepay_amount), 2)


def get_safepay_base_url():
    """Get configured Safepay base URL or default to sandbox."""
    return current_app.config.get('SAFEPAY_BASE_URL', 'https://sandbox.api.getsafepay.com')


def verify_safepay_order(tracker_token: str, expected_charges=None, expected_currency='PKR'):
    """
    Verify a payment tracker with Safepay's Order API v1.
    Confirms:
      1. Tracker state is paid (TRACKER_ENDED / PAYMENT_SUCCESSFUL / CHARGED).
      2. Currency is exactly expected_currency (default 'PKR').
      3. Paid amount matches expected_charges in the same unit (PKR Rupees).
    Returns:
      (is_valid: bool, reason: str, order_data: dict)
    """
    if not tracker_token:
        return False, "Missing tracker token", {}

    base_url = get_safepay_base_url()
    try:
        resp = http_requests.get(
            f"{base_url}/order/v1/{tracker_token}",
            headers=SAFEPAY_HEADERS,
            timeout=10
        )
        if resp.status_code != 200:
            msg = f"Safepay tracker lookup failed: HTTP {resp.status_code}"
            logger.warning("[SAFEPAY] %s: %s", msg, resp.text[:200])
            return False, msg, {}

        data = resp.json().get('data', {})
        state = data.get('state', '')
        currency = (data.get('currency') or '').strip().upper()
        raw_amount = data.get('amount')

        logger.info("[SAFEPAY] Tracker %s state=%s currency=%s amount=%s", tracker_token, state, currency, raw_amount)

        if state not in ('TRACKER_ENDED', 'PAYMENT_SUCCESSFUL', 'CHARGED'):
            return False, f"Payment not finalized (state={state})", data

        # Validate currency
        if expected_currency and currency != expected_currency.upper():
            err = f"Currency mismatch: received {currency}, expected {expected_currency.upper()}"
            logger.error("[SAFEPAY REJECTED] Tracker %s %s", tracker_token, err)
            return False, err, data

        # Validate amount
        if expected_charges is not None:
            paid_amount = from_safepay_amount(raw_amount)
            expected_amount = round(float(expected_charges), 2)
            if abs(paid_amount - expected_amount) > 0.01:
                err = f"Amount mismatch: received Rs. {paid_amount}, expected Rs. {expected_amount}"
                logger.error("[SAFEPAY REJECTED] Tracker %s %s", tracker_token, err)
                return False, err, data

        return True, "Payment verified successfully", data

    except Exception as e:
        logger.error("[SAFEPAY] Verification error for %s: %s", tracker_token, e)
        return False, f"Verification error: {e}", {}

