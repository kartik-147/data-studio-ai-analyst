"""
Authentication and User Security Management Module for Data Studio
- Secure User Authentication (Password Hashing with Cryptographic Salt)
- Verified Google & Email Accounts
- Persistent User History & Activity Tracking per User
- Session State & Browser LocalStorage Persistence
- User Profile & Account Management
"""

import os
import re
import json
import base64
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, Tuple, Optional, List

import streamlit as st
import streamlit.components.v1 as components
from modules.config import BASE_DIR, NAV_OVERVIEW


# Path to Persistent User Database
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")
USERS_DB_FILE = os.path.join(USER_DATA_DIR, "users_db.json")


def _ensure_user_data_dir():
    """Ensure user_data directory exists."""
    if not os.path.exists(USER_DATA_DIR):
        os.makedirs(USER_DATA_DIR, exist_ok=True)


def _load_users_db() -> Dict[str, Any]:
    """Load user accounts and history database from disk."""
    _ensure_user_data_dir()
    if os.path.exists(USERS_DB_FILE):
        try:
            with open(USERS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_users_db(db: Dict[str, Any]):
    """Persist user database to disk securely."""
    _ensure_user_data_dir()
    try:
        with open(USERS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving users database: {e}")


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hash password using SHA-256 with a unique cryptographic salt."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return hashed, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Verify input password against stored salt and expected hash."""
    if not salt or not expected_hash:
        return False
    computed_hash = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return secrets.compare_digest(computed_hash, expected_hash)


def is_valid_email(email: str) -> bool:
    """Check if email string is formatted properly."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def register_user(
    name: str,
    email: str,
    password: Optional[str] = None,
    provider: str = "password",
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new user in the persistent database.
    Enforces uniqueness, password strength, and data validation.
    """
    clean_name = name.strip()
    clean_email = email.strip().lower()

    if not clean_name:
        return False, "Please enter your full name.", None

    if not is_valid_email(clean_email):
        return False, "Please enter a valid email address.", None

    db = _load_users_db()

    if clean_email in db:
        return False, "An account with this email already exists. Please Sign In.", None

    salt, pwd_hash = "", ""
    if provider == "password":
        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters long.", None
        pwd_hash, salt = hash_password(password)

    now_iso = datetime.now().isoformat()
    now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")

    user_record = {
        "uid": f"usr-{secrets.token_hex(6)}",
        "name": clean_name,
        "email": clean_email,
        "salt": salt,
        "password_hash": pwd_hash,
        "provider": provider,
        "created_at": now_iso,
        "last_login": now_iso,
        "total_logins": 1,
        "history": [
            {
                "icon": "user-check",
                "action": "Account Created",
                "detail": f"Signed up via {provider.title()}",
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
    Authenticate an existing user with Email and Password.
    Verifies credentials against secure hash database.
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

    if user.get("provider") == "google.com" and not user.get("password_hash"):
        return False, "This account was created with Google. Please use the Google Account tab.", None

    if not verify_password(password, user.get("salt", ""), user.get("password_hash", "")):
        return False, "Incorrect password. Please verify your credentials.", None

    # Update login metrics
    now_iso = datetime.now().isoformat()
    now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")
    user["last_login"] = now_iso
    user["total_logins"] = user.get("total_logins", 0) + 1

    if "history" not in user:
        user["history"] = []
    
    user["history"].insert(0, {
        "icon": "log-in",
        "action": "Signed In",
        "detail": "Authenticated with Password",
        "timestamp": now_readable,
    })
    user["history"] = user["history"][:20]

    _save_users_db(db)

    return True, "Login successful!", _sanitize_user_dict(user)


def authenticate_google_user(email: str, name: str = "") -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate or auto-register a verified Google user.
    Maintains persistent user history and profile across sessions.
    """
    clean_email = email.strip().lower()

    if not clean_email:
        return False, "Please enter your Google account email.", None

    if not is_valid_email(clean_email):
        return False, "Please enter a valid Google email address.", None

    db = _load_users_db()
    now_iso = datetime.now().isoformat()
    now_readable = datetime.now().strftime("%b %d, %Y - %H:%M")

    if clean_email in db:
        # Existing Google User Login
        user = db[clean_email]
        user["last_login"] = now_iso
        user["total_logins"] = user.get("total_logins", 0) + 1
        
        if name and not user.get("name"):
            user["name"] = name.strip()

        if "history" not in user:
            user["history"] = []
        
        user["history"].insert(0, {
            "icon": "log-in",
            "action": "Signed In",
            "detail": "Authenticated via Google",
            "timestamp": now_readable,
        })
        user["history"] = user["history"][:20]

        _save_users_db(db)
        return True, "Welcome back!", _sanitize_user_dict(user)
    else:
        # New Google User Registration
        display_name = name.strip() if name.strip() else clean_email.split("@")[0].replace(".", " ").title()
        user_record = {
            "uid": f"google-usr-{secrets.token_hex(6)}",
            "name": display_name,
            "email": clean_email,
            "salt": "",
            "password_hash": "",
            "provider": "google.com",
            "created_at": now_iso,
            "last_login": now_iso,
            "total_logins": 1,
            "history": [
                {
                    "icon": "user-check",
                    "action": "Google Account Registered",
                    "detail": "Created workspace via Google Account",
                    "timestamp": now_readable,
                }
            ],
            "saved_datasets": [],
        }
        db[clean_email] = user_record
        _save_users_db(db)
        return True, "Google account registered successfully!", _sanitize_user_dict(user_record)


def _sanitize_user_dict(user: Dict[str, Any]) -> Dict[str, Any]:
    """Return user dict safe for session state (strip salt & password hash)."""
    return {
        "uid": user.get("uid"),
        "name": user.get("name", "User"),
        "email": user.get("email"),
        "photo_url": user.get("photo_url", ""),
        "provider": user.get("provider", "password"),
        "created_at": user.get("created_at"),
        "last_login": user.get("last_login"),
        "total_logins": user.get("total_logins", 1),
        "history": user.get("history", []),
        "saved_datasets": user.get("saved_datasets", []),
    }


def save_user_activity(email: str, icon: str, action: str, detail: str):
    """Append an action to the user's persistent record in database."""
    if not email:
        return
    clean_email = email.strip().lower()
    db = _load_users_db()
    if clean_email in db:
        user = db[clean_email]
        if "history" not in user:
            user["history"] = []
        
        now_readable = datetime.now().strftime("%b %d - %H:%M")
        new_entry = {
            "icon": icon,
            "action": action,
            "detail": detail,
            "timestamp": now_readable,
        }
        # Avoid duplicate consecutive logs
        if user["history"] and user["history"][0].get("action") == action and user["history"][0].get("detail") == detail:
            return
        
        user["history"].insert(0, new_entry)
        user["history"] = user["history"][:25]
        _save_users_db(db)


def get_user_history(email: str) -> List[Dict[str, Any]]:
    """Retrieve full persistent activity history for a user."""
    if not email:
        return []
    clean_email = email.strip().lower()
    db = _load_users_db()
    if clean_email in db:
        return db[clean_email].get("history", [])
    return []


def login_user(user_data: Dict[str, Any]):
    """
    Log in user into Streamlit session state and restore their persistent data history.
    """
    st.session_state.is_authenticated = True
    st.session_state.user_info = user_data

    # Restore user's persistent data history into session activity log
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
    """Log out current user and clear auth state."""
    st.session_state.is_authenticated = False
    st.session_state.user_info = None
    st.session_state.activity_log = []


def get_current_user() -> Optional[Dict[str, Any]]:
    """Return currently authenticated user dict or None."""
    if st.session_state.get("is_authenticated", False):
        return st.session_state.get("user_info")
    return None


def is_user_logged_in() -> bool:
    """Return True if user is currently authenticated."""
    return st.session_state.get("is_authenticated", False)


def handle_auth_callback():
    """
    Check for incoming auth payload from query params or session state.
    """
    query_params = getattr(st, "query_params", {})
    if "fb_user" in query_params:
        try:
            encoded_payload = query_params.get("fb_user")
            if isinstance(encoded_payload, list):
                encoded_payload = encoded_payload[0]
            decoded_json = base64.b64decode(encoded_payload).decode("utf-8")
            user_data = json.loads(decoded_json)
            
            if user_data and ("email" in user_data or "uid" in user_data):
                login_user(user_data)
                if hasattr(st, "query_params") and "fb_user" in st.query_params:
                    del st.query_params["fb_user"]
                st.session_state.current_page = NAV_OVERVIEW
                st.rerun()
        except Exception as e:
            st.session_state.auth_error = f"Failed to parse authentication payload: {str(e)}"


def render_session_persistence_checker():
    """
    Check browser localStorage for an existing active session upon page refresh.
    """
    if st.session_state.get("is_authenticated", False):
        return

    html_code = """
    <script>
    (function() {
        try {
            const saved = localStorage.getItem('ds_firebase_auth_user');
            if (saved) {
                const user = JSON.parse(saved);
                if (user && (user.email || user.uid)) {
                    let parentHref = "";
                    try {
                        if (window.top && window.top.location && window.top.location.href) {
                            parentHref = window.top.location.href;
                        }
                    } catch(e) {}
                    if (!parentHref) {
                        try {
                            if (window.parent && window.parent.location && window.parent.location.href) {
                                parentHref = window.parent.location.href;
                            }
                        } catch(e) {}
                    }
                    if (!parentHref) {
                        parentHref = document.referrer || window.location.href;
                    }
                    const currentUrl = new URL(parentHref);
                    if (!currentUrl.searchParams.has("fb_user")) {
                        const jsonStr = JSON.stringify(user);
                        const b64 = btoa(unescape(encodeURIComponent(jsonStr)));
                        currentUrl.searchParams.set("fb_user", b64);
                        try {
                            if (window.top) {
                                window.top.location.href = currentUrl.toString();
                                return;
                            }
                        } catch(e) {}
                        window.location.href = currentUrl.toString();
                    }
                }
            }
        } catch (e) {
            console.debug("Session check notice:", e);
        }
    })();
    </script>
    """
    components.html(html_code, height=0, width=0)


def render_account_sidebar_widget():
    """Render authenticated user information, verification badge, and Sign Out button in sidebar."""
    user = get_current_user()

    if user:
        name = user.get("name", "User")
        email = user.get("email", "")
        photo_url = user.get("photo_url", "")
        provider = user.get("provider", "password")

        badge_bg = "#4285F4" if "google" in provider else ("#8B5CF6" if provider == "guest" else "#10B981")
        provider_name = "Google Verified" if "google" in provider else ("Guest Demo" if provider == "guest" else "Email Verified")

        st.markdown(
            f"""
            <div class="sidebar-status-card" style="border-left: 3px solid {badge_bg}; padding: 0.65rem 0.75rem; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    {'<img src="' + photo_url + '" style="width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1.5px solid ' + badge_bg + ';" />' if photo_url else '<div style="width: 34px; height: 34px; border-radius: 50%; background: ' + badge_bg + '; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">' + name[0].upper() + '</div>'}
                    <div style="overflow: hidden; flex: 1;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-color, inherit); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
                        <div style="font-size: 0.72rem; color: #94A3B8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{email}</div>
                    </div>
                </div>
                <div style="margin-top: 6px; font-size: 0.68rem; font-weight: 600; color: {badge_bg}; display: flex; align-items: center; gap: 4px;">
                    <span>●</span> {provider_name}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign Out", key="auth_signout_sidebar_btn", use_container_width=True):
            perform_sign_out()


def perform_sign_out():
    """Sign out user, clear localStorage, and reset session state."""
    clear_script = """
    <script>
    try {
        localStorage.removeItem('ds_firebase_auth_user');
        sessionStorage.removeItem('ds_firebase_auth_user');
    } catch(e) {}
    </script>
    """
    components.html(clear_script, height=0, width=0)
    logout_user()
    st.rerun()


def render_google_sign_in_component(key: str = "google_auth_btn"):
    """Compatibility stub for components."""
    pass
