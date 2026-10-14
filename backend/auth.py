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


def verify_google_credentials(email: str, password_or_code: str):
    """
    Live verification against Google's authentication servers.
    Verifies Gmail credentials via SSL directly with Google, or via Google OAuth2 token.
    """
    import imaplib
    import urllib.request
    import json

    cleaned_email = email.strip().lower()
    cleaned_cred = password_or_code.strip()

    # 1. If credential is a Google OAuth ID Token (JWT format)
    if cleaned_cred.startswith("eyJ") and "." in cleaned_cred:
        try:
            req = urllib.request.Request(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={cleaned_cred}",
                headers={"User-Agent": "TalentPulse-AI"}
            )
            with urllib.request.urlopen(req, timeout=6) as response:
                token_data = json.loads(response.read().decode())
                if token_data.get("email", "").lower() != cleaned_email:
                    raise HTTPException(
                        status_code=401,
                        detail="Google Token Mismatch: The authenticated Google account does not match the entered email."
                    )
                return True
        except urllib.error.HTTPError:
            raise HTTPException(
                status_code=401,
                detail="Google Authentication Failed: The provided Google ID token is invalid or expired."
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Google token verification failed: {str(e)}")

    # 2. Live verification directly with Google authentication servers (IMAP SSL)
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=7)
        mail.login(cleaned_email, cleaned_cred)
        mail.logout()
        return True
    except imaplib.IMAP4.error as err:
        raise HTTPException(
            status_code=401,
            detail="Google Authentication Failed: Incorrect password or invalid Google credentials. Google rejected the login attempt. If you have 2-Step Verification enabled on Gmail, please use a Google App Password (myaccount.google.com/apppasswords)."
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"Could not connect to Google authentication servers: {str(e)}"
        )


def verify_github_credentials(email_or_username: str, token_or_pwd: str):
    """
    Live verification against GitHub API.
    """
    import urllib.request
    import json

    token_clean = token_or_pwd.strip()
    try:
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {token_clean}", "User-Agent": "TalentPulse-AI"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            gh_data = json.loads(resp.read().decode())
            return gh_data.get("login") or gh_data.get("name") or "GitHub User"
    except urllib.error.HTTPError as err:
        if err.code == 401:
            raise HTTPException(
                status_code=401,
                detail="GitHub Authorization Failed: Invalid GitHub Personal Access Token or credentials. GitHub rejected authorization."
            )
        raise HTTPException(status_code=err.code, detail=f"GitHub API Error: {err.reason}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not connect to GitHub API: {str(e)}")

