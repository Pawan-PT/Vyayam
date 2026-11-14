"""Classify a Hugging Face failure into a stable code, a one-line reason and the exact fix.

diagnose(exc, context) -> dict with: code, ok, reason, fix, status, message, context.
Reads only the exception and its response body. It never touches headers or the
environment, and it redacts anything shaped like an HF credential from the message.
"""
import re

MAX_MESSAGE = 500
PLAN_WORDS = ("payment", "billing", "quota", "subscription")
SECRET_SHAPE = re.compile(r"hf_[A-Za-z0-9]{16,}")

_VERDICTS = {
    "TOKEN_INVALID": (
        "The HF token is wrong, expired or revoked.",
        "Create a new classic token of type Write at https://huggingface.co/settings/tokens "
        "and save it as the HF_TOKEN repo secret.",
    ),
    "TOKEN_FORBIDDEN": (
        "The token is valid but not allowed to do this; usually a fine-grained token without "
        "write/repo-create permission on your namespace.",
        "Replace the HF_TOKEN repo secret with a CLASSIC token of type Write.",
    ),
    "PLAN_REQUIRED": (
        "The account needs a paid plan or a payment method for this.",
        "Add a payment method or upgrade the plan at https://huggingface.co/settings/billing.",
    ),
    "ALREADY_EXISTS": ("The Space already exists. Not a failure.", "None needed."),
    "UNKNOWN": ("Unrecognized failure.", "Read the HF message below."),
}


def _status(exc):
    status = getattr(getattr(exc, "response", None), "status_code", None)
    return status if isinstance(status, int) else None


def _body(exc):
    try:
        text = getattr(getattr(exc, "response", None), "text", None)
        if isinstance(text, str) and text.strip():
            return text
    except Exception:
        pass
    return str(exc)


def diagnose(exc, context=""):
    status = _status(exc)
    body = _body(exc)
    if status == 402:
        code = "PLAN_REQUIRED"
    elif status == 401:
        code = "TOKEN_INVALID"
    elif status == 409:
        code = "ALREADY_EXISTS"
    elif any(w in body.lower() for w in PLAN_WORDS):
        code = "PLAN_REQUIRED"
    elif status == 403:
        code = "TOKEN_FORBIDDEN"
    else:
        code = "UNKNOWN"
    reason, fix = _VERDICTS[code]
    if code == "UNKNOWN":
        reason = f"Unrecognized failure (HTTP {status if status is not None else 'n/a'})."
    return {
        "code": code,
        "ok": code == "ALREADY_EXISTS",
        "reason": f"{reason} [at {context}]" if context else reason,
        "fix": fix,
        "status": status,
        "message": SECRET_SHAPE.sub("[redacted]", body)[:MAX_MESSAGE],
        "context": context,
    }
