"""
Authentication & Security Engine for TalentPulse.
Provides password hashing with PBKDF2, anti-bot Captcha generation and verification,
validation checks, and Google / GitHub OAuth integrations.
"""

import os
import re
import time
import uuid
import hashlib
import random
from typing import Dict, Tuple, Optional
from datetime import datetime, timezone

from fastapi import HTTPException, Header, Depends
from sqlalchemy.orm import Session

from backend.database import UserModel, get_db

# In-memory captcha token store (token -> {answer: str, expires_at: float})
_CAPTCHA_STORE: Dict[str, Dict] = {}


def generate_captcha() -> Dict[str, str]:
    """
    Generates a secure captcha challenge.
    Cleans expired captchas and returns token + challenge text.
    """
    now = time.time()
    # Prune expired tokens
    expired = [k for k, v in _CAPTCHA_STORE.items() if v["expires_at"] < now]
    for k in expired:
        _CAPTCHA_STORE.pop(k, None)

    num1 = random.randint(12, 45)
    num2 = random.randint(3, 29)
    answer = str(num1 + num2)
    challenge = f"{num1} + {num2} = ?"

    token = str(uuid.uuid4())
    _CAPTCHA_STORE[token] = {
        "answer": answer,
        "expires_at": now + 300  # 5 minutes validity
    }
    return {
        "captcha_token": token,
        "captcha_question": challenge
    }


def verify_captcha(token: str, answer: str) -> bool:
    """Verifies user answer against stored token."""
    if not token or not answer:
        return False
    now = time.time()
    record = _CAPTCHA_STORE.get(token)
    if not record or record["expires_at"] < now:
        return False
    # One-time use: delete on attempt
    _CAPTCHA_STORE.pop(token, None)
    return record["answer"].strip().lower() == answer.strip().lower()


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes password with PBKDF2-HMAC-SHA256 and unique cryptographic salt."""
    if not salt:
        salt = os.urandom(16).hex()
    pwd_bytes = password.encode("utf-8")
    salt_bytes = salt.encode("utf-8")
    key = hashlib.pbkdf2_hmac("sha256", pwd_bytes, salt_bytes, 100_000)
    return salt, key.hex()


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, computed_hash = hash_password(password, salt)
    return computed_hash == expected_hash


def validate_email_format(email: str):
    """Enforces standard email address formatting."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, email.strip()):
        raise HTTPException(status_code=400, detail="Invalid email address format.")


def validate_password_strength(password: str):
    """Enforces minimum 6 characters with both letters and numbers."""
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise HTTPException(status_code=400, detail="Password must contain at least one letter and one number.")


def generate_session_token() -> str:
    return f"tp_{uuid.uuid4().hex}_{int(time.time())}"


def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """Extracts authenticated user from Bearer header if present."""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    user = db.query(UserModel).filter(UserModel.session_token == token).first()
    return user
