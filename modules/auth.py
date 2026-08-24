"""
Authentication and User Security Management Module for Data Studio
===================================================================

AUTHENTICATION ARCHITECTURE:
----------------------------
1. Google OAuth 2.0 / OpenID Connect (OIDC):
   - Native integration using Streamlit's official `st.login()`, `st.user`, and `st.logout()`.
   - Credentials configured in `.streamlit/secrets.toml` under `[auth]` (Client ID, Client Secret, Cookie Secret).
   - Identity claims (email, name, sub/id, picture) are cryptographically validated by Google and Streamlit server.
   
2. Standard Email & Password:
   - Passwords hashed using bcrypt with cryptographically secure salts (`bcrypt.gensalt(12)`).
   - Stored in persistent user database without raw passwords.

3. Guest Demo Access:
   - Isolated sandbox session mode for evaluation.

DATABASE ARCHITECTURE & MIGRATION NOTE:
---------------------------------------
This module persists user accounts and audit history to a local JSON storage file (`user_data/users_db.json`).
On ephemeral hosting environments (Streamlit Community Cloud, Cloud Run), local files may reset on redeployment.
For persistent multi-instance cloud deployments, replace `_load_users_db()` and `_save_users_db()` with:
  - Google Cloud Firestore (`firebase-admin` / `google-cloud-firestore`)
  - Supabase / PostgreSQL (`supabase-py` / `psycopg2`)
"""

import os
import re
import json
import secrets
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

import bcrypt
import streamlit as st
from modules.config import BASE_DIR, NAV_OVERVIEW


# ==============================================================================
# Persistent Database Layer (Local JSON Storage)
# ==============================================================================

USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
USERS_DB_FILE = os.path.join(USER_DATA_DIR, "users_db.json")


def _ensure_user_data_dir():
    """Ensure user_data storage directory exists."""
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, exist_ok=True)


def _load_users_db() -> Dict[str, Any]:
    """
    Load user accounts and history database from disk.
    Returns dictionary indexed by normalized lowercase email.
    """
    _ensure_user_data_dir()
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"[AUTH DB] Error reading users database: {e}")
            return {}
    return {}


def _save_users_db(db: Dict[str, Any]):
    """
    Persist user database to disk securely with atomic write.
    """
    _ensure_user_data_dir()
    try:
        temp_file = f"{USERS_DB_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
        if os.path.exists(USERS_DB_FILE):
            os.replace(temp_file, USERS_DB_FILE)
        else:
            os.rename(temp_file, USERS_DB_FILE)
    except Exception as e:
        print(f"[AUTH DB] Error saving users database: {e}")


# ==============================================================================
# Cryptographic Password Hashing & Validation
# ==============================================================================

def hash_password(password: str) -> str:
    """
    Hash a plain-text password using bcrypt with a secure random salt.
    """
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a plain-text password against a stored bcrypt hash.
    """
    if not password or not hashed_password:
        return False
    try:
        pwd_bytes = password.encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception as e:
        print(f"[AUTH SECURITY] Password verification exception: {e}")
        return False


def is_valid_email(email: str) -> bool:
    """Validate email format using standardized RFC regex pattern."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


# ==============================================================================
# Google OpenID Connect / OAuth Integration Layer
# ==============================================================================

def is_google_oauth_configured() -> bool:
    """
    Check if Google OAuth / OIDC secrets are configured in Streamlit secrets.
    Safely handles absence of secrets.toml without raising exceptions.
    """
    try:
        if hasattr(st, "secrets") and "auth" in st.secrets:
            auth_sec = st.secrets["auth"]
            if "client_id" in auth_sec and "client_secret" in auth_sec:
                return True
            if "google" in auth_sec and isinstance(auth_sec["google"], dict):
                g_sec = auth_sec["google"]
                if "client_id" in g_sec and "client_secret" in g_sec:
                    return True
    except Exception:
        return False
    return False


def initiate_google_login():
    """
    Initiate official Google OAuth login flow via Streamlit native OpenID Connect.
    Redirects user directly to accounts.google.com authentication page.
    """
    if not is_google_oauth_configured():
        st.error(
            "Google OAuth is not configured yet. "
            "Please copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` "
            "and add your Google OAuth Client ID and Client Secret."
        )
        return

    try:
        if hasattr(st, "login"):
            try:
                if hasattr(st, "secrets") and "auth" in st.secrets and "google" in st.secrets.get("auth", {}):
                    st.login("google")
                    return
            except Exception:
                pass
            st.login()
        else:
            st.error("Streamlit native login is not supported in this environment.")
    except Exception as e:
        st.error(f"Google OAuth Redirection Error: {str(e)}")


def sync_oauth_user_session():
    """
    Synchronize verified Google OpenID Connect identity from `st.user` into session state.
    Executes automatically upon OAuth callback redirection.
    """
    if hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
        user_dict = st.user.to_dict() if hasattr(st.user, "to_dict") else {}
        
        google_email = (
            getattr(st.user, "email", None)
            or user_dict.get("email")
            or (st.user.get("email") if hasattr(st.user, "get") else None)
        )

        if google_email:
            clean_email = str(google_email).strip().lower()
            google_name = (
                getattr(st.user, "name", None)
                or user_dict.get("name")
                or (st.user.get("name") if hasattr(st.user, "get") else None)
                or clean_email.split("@")[0].replace(".", " ").title()
            )
            google_sub = str(
                user_dict.get("sub")
                or user_dict.get("id")
                or (st.user.get("sub") if hasattr(st.user, "get") else None)
                or secrets.token_hex(6)
            )
            google_picture = str(
                user_dict.get("picture")
                or (st.user.get("picture") if hasattr(st.user, "get") else "")
                or ""
            )

            # Persist or update verified Google user in database
            db = _load_users_db()
            now_iso = datetime.now().isoformat()
            now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")

            if clean_email in db:
                user_record = db[clean_email]
                user_record["name"] = google_name
                user_record["display_name"] = google_name
                user_record["photo_url"] = google_picture
                user_record["last_login"] = now_iso
                user_record["total_logins"] = user_record.get("total_logins", 0) + 1
                user_record["provider"] = "google.com"
                user_record["google_sub"] = google_sub

                if "history" not in user_record or not isinstance(user_record["history"], list):
                    user_record["history"] = []

                if not user_record["history"] or user_record["history"][0].get("action") != "Google OAuth Sign In":
                    user_record["history"].insert(0, {
                        "icon": "log-in",
                        "action": "Google OAuth Sign In",
                        "detail": "Verified via Google OpenID Connect",
                        "timestamp": now_readable,
                    })
                    user_record["history"] = user_record["history"][:25]

                db[clean_email] = user_record
                _save_users_db(db)
            else:
                user_record = {
                    "uid": f"google-{google_sub[:12]}",
                    "google_sub": google_sub,
                    "name": google_name,
                    "display_name": google_name,
                    "email": clean_email,
                    "photo_url": google_picture,
                    "password_hash": "",
                    "provider": "google.com",
                    "created_at": now_iso,
                    "last_login": now_iso,
                    "total_logins": 1,
                    "history": [
                        {
                            "icon": "user-check",
                            "action": "Google Account Registered",
                            "detail": "Created workspace via Google OpenID Connect",
                            "timestamp": now_readable,
                        }
                    ],
                    "saved_datasets": [],
                }
                db[clean_email] = user_record
                _save_users_db(db)

            # Establish authenticated session
            sanitized = _sanitize_user_dict(user_record)
            st.session_state.authenticated = True
            st.session_state.is_authenticated = True
            st.session_state.user_info = sanitized


# ==============================================================================
# Core User Account & Authentication Operations
# ==============================================================================

def create_user(
    name: str,
    email: str,
    password: str,
    password_confirm: str,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new user account with full credential verification.
    """
    clean_name = name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return False, "Please enter your full name.", None

    if not clean_email or not is_valid_email(clean_email):
        return False, "Please enter a valid email address.", None

    if not password:
        return False, "Please enter a password.", None

    if len(password) < 6:
        return False, "Password must be at least 6 characters long.", None

    if password != password_confirm:
        return False, "Passwords do not match. Please re-type your password.", None

    db = _load_users_db()

    if clean_email in db:
        return False, "An account with this email already exists. Please Sign In.", None

    pwd_hash = hash_password(password)
    now_iso = datetime.now().isoformat()
    now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")

    user_record = {
        "uid": f"usr-{secrets.token_hex(6)}",
        "email": clean_email,
        "password_hash": pwd_hash,
        "display_name": clean_name,
        "name": clean_name,
        "photo_url": "",
        "provider": "email_password",
        "created_at": now_iso,
        "last_login": now_iso,
        "total_logins": 1,
        "history": [
            {
                "icon": "user-check",
                "action": "Account Created",
                "detail": "Registered secure email/password account",
                "timestamp": now_readable,
            }
        ],
        "saved_datasets": [],
    }

    db[clean_email] = user_record
    _save_users_db(db)

    return True, "Account registered successfully!", _sanitize_user_dict(user_record)


def authenticate_user(email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate an existing user with verified Email and Password.
    """
    clean_email = email.strip().lower()

    if not clean_email:
        return False, "Please enter your email address.", None

    if not password:
        return False, "Please enter your password.", None

    db = _load_users_db()

    if clean_email not in db:
        return False, "No account found with this email. Please click 'Create Account' first.", None

    user = db[clean_email]
    stored_hash = user.get("password_hash", "")

    if not stored_hash:
        # If an account existed without a password, set their password now
        stored_hash = hash_password(password)
        user["password_hash"] = stored_hash
        user["provider"] = "email_password"
    elif not verify_password(password, stored_hash):
        return False, "Incorrect password. Please verify your credentials.", None

    now_iso = datetime.now().isoformat()
    now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")
    user["last_login"] = now_iso
    user["total_logins"] = user.get("total_logins", 0) + 1

    if "history" not in user or not isinstance(user["history"], list):
        user["history"] = []

    user["history"].insert(0, {
        "icon": "log-in",
        "action": "Signed In",
        "detail": "Authenticated with verified password",
        "timestamp": now_readable,
    })
    user["history"] = user["history"][:25]

    db[clean_email] = user
    _save_users_db(db)

    return True, "Login successful!", _sanitize_user_dict(user)


def login_guest_user() -> Dict[str, Any]:
    """
    Establish an isolated Guest Demo session for evaluation.
    """
    guest_user = {
        "uid": "guest-analyst-demo",
        "email": "guest@datastudiokb.local",
        "display_name": "Guest Analyst",
        "name": "Guest Analyst",
        "photo_url": "",
        "provider": "guest",
        "created_at": datetime.now().isoformat(),
        "last_login": datetime.now().isoformat(),
        "total_logins": 1,
        "history": [
            {
                "icon": "user",
                "action": "Guest Demo Session",
                "detail": "Logged in as Guest Analyst",
                "timestamp": datetime.now().strftime("%b %d - %H:%M"),
            }
        ],
        "saved_datasets": [],
    }
    login_user(guest_user)
    return guest_user


def _sanitize_user_dict(user: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return sanitized user dictionary safe for session state.
    """
    display_name = user.get("display_name") or user.get("name", "User")
    return {
        "uid": user.get("uid"),
        "email": user.get("email"),
        "display_name": display_name,
        "name": display_name,
        "photo_url": user.get("photo_url", ""),
        "provider": user.get("provider", "email_password"),
        "google_sub": user.get("google_sub", ""),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
        "total_logins": user.get("total_logins", 1),
        "history": user.get("history", []),
        "saved_datasets": user.get("saved_datasets", []),
    }


# ==============================================================================
# Session Management & Route Protection
# ==============================================================================

def login_user(user_data: Dict[str, Any]):
    """
    Attach verified user identity into Streamlit session state.
    """
    st.session_state.authenticated = True
    st.session_state.is_authenticated = True
    st.session_state.user_info = user_data

    email = user_data.get("email", "")
    if email and user_data.get("provider") != "guest":
        db = _load_users_db()
        clean_email = email.lower()
        if clean_email in db:
            user_rec = db[clean_email]
            st.session_state.activity_log = user_rec.get("history", []).copy()

    if "current_page" not in st.session_state or not st.session_state.current_page:
        st.session_state.current_page = NAV_OVERVIEW


def logout_user():
    """
    Completely clear user session state and authentication tokens.
    """
    st.session_state.authenticated = False
    st.session_state.is_authenticated = False
    st.session_state.user_info = None
    st.session_state.activity_log = []


def perform_sign_out():
    """
    Execute full sign out.
    If authenticated via Google OAuth, invoke st.logout() to clear OIDC cookie.
    """
    user = get_current_user()
    is_oauth_user = user and user.get("provider") == "google.com"

    logout_user()

    if is_oauth_user and hasattr(st, "logout") and hasattr(st, "user") and getattr(st.user, "is_logged_in", False):
        st.logout()
    else:
        st.rerun()


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Return currently authenticated user dict if session is valid, else None.
    """
    if is_user_logged_in():
        return st.session_state.get("user_info")
    return None


def is_user_logged_in() -> bool:
    """
    Verify that an active, validated session exists in Streamlit session state.
    """
    has_auth_flag = bool(st.session_state.get("authenticated", False) or st.session_state.get("is_authenticated", False))
    user_info = st.session_state.get("user_info")
    return has_auth_flag and isinstance(user_info, dict) and bool(user_info.get("email"))


def verify_session() -> bool:
    """Alias for `is_user_logged_in()`."""
    return is_user_logged_in()


def render_account_sidebar_widget():
    """Render authenticated user profile card with real provider badges and Sign Out button."""
    user = get_current_user()

    if user:
        name = user.get("display_name") or user.get("name", "User")
        email = user.get("email", "")
        photo_url = user.get("photo_url", "")
        provider = user.get("provider", "email_password")

        if provider == "google.com":
            badge_color = "#4285F4"
            provider_label = "Google Verified"
        elif provider == "guest":
            badge_color = "#8B5CF6"
            provider_label = "Guest Demo"
        else:
            badge_color = "#10B981"
            provider_label = "Email Verified"

        avatar_content = (
            f'<img src="{photo_url}" style="width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1.5px solid {badge_color};" />'
            if photo_url
            else f'<div style="width: 34px; height: 34px; border-radius: 50%; background: {badge_color}; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">{name[0].upper()}</div>'
        )

        st.markdown(
            f"""
            <div class="sidebar-status-card" style="border-left: 3px solid {badge_color}; padding: 0.65rem 0.75rem; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    {avatar_content}
                    <div style="overflow: hidden; flex: 1;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-color, inherit); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
                        <div style="font-size: 0.72rem; color: #94A3B8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{email}</div>
                    </div>
                </div>
                <div style="margin-top: 6px; font-size: 0.68rem; font-weight: 600; color: {badge_color}; display: flex; align-items: center; gap: 4px;">
                    <span>●</span> {provider_label}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="auth_signout_sidebar_btn", use_container_width=True):
            perform_sign_out()


# ==============================================================================
# Persistent Activity Tracking
# ==============================================================================

def save_user_activity(email: str, icon: str, action: str, detail: str):
    """Append an action to the user's persistent record in database."""
    if not email:
        return
    clean_email = email.strip().lower()
    db = _load_users_db()
    if clean_email in db:
        user = db[clean_email]
        if "history" not in user or not isinstance(user["history"], list):
            user["history"] = []

        now_readable = datetime.now().strftime("%b %d - %H:%M")
        new_entry = {
            "icon": icon,
            "action": action,
            "detail": detail,
            "timestamp": now_readable,
        }
        if user["history"] and user["history"][0].get("action") == action and user["history"][0].get("detail") == detail:
            return

        user["history"].insert(0, new_entry)
        user["history"] = user["history"][:25]
        _save_users_db(db)


def get_user_history(email: str) -> List[Dict[str, Any]]:
    """Retrieve persistent activity audit history for a user."""
    if not email:
        return []
    clean_email = email.strip().lower()
    db = _load_users_db()
    if clean_email in db:
        return db[clean_email].get("history", [])
    return []
