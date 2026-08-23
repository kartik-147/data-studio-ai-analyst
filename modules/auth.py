"""
Authentication Module for Data Studio
- Real Firebase Google Authentication with GoogleAuthProvider & signInWithPopup
- Dedicated OAuth Popup Window Flow with postMessage & localStorage session sync
- Session State & Browser Local Persistence
- Sidebar & Settings Page User Profile Integration
"""

import json
import base64
import streamlit as st
import streamlit.components.v1 as components
from modules.config import get_firebase_config, login_user, logout_user, NAV_OVERVIEW


def handle_auth_callback():
    """
    Check for incoming auth payload from query params or session state.
    Decodes user info, persists it to session state, and clears the URL params.
    """
    query_params = getattr(st, "query_params", {})
    if "fb_user" in query_params:
        try:
            encoded_payload = query_params.get("fb_user")
            if isinstance(encoded_payload, list):
                encoded_payload = encoded_payload[0]
            
            # Decode base64 payload
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


def get_current_user():
    """Return currently authenticated user dict or None."""
    if st.session_state.get("is_authenticated", False):
        return st.session_state.get("user_info")
    return None


def is_user_logged_in() -> bool:
    """Return True if user is currently authenticated."""
    return st.session_state.get("is_authenticated", False)


def render_session_persistence_checker():
    """
    Check browser localStorage for an existing active session upon page refresh.
    If authenticated in localStorage but not in Streamlit session state, restore session.
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


def render_google_sign_in_component(key: str = "main_google_auth", is_signup: bool = False):
    """
    Render Firebase Google Sign-In button that launches real Google popup authentication.
    Handles both Sign In and Sign Up flows seamlessly.
    """
    fb_config = get_firebase_config()
    fb_config_json = json.dumps(fb_config)
    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"
    btn_text_label = "Sign up with Google" if is_signup else "Continue with Google"

    btn_bg = "#111827" if is_dark else "#FFFFFF"
    btn_border = "#1F2937" if is_dark else "#E2E8F0"
    btn_text = "#F8FAFC" if is_dark else "#0F172A"
    btn_hover_bg = "#1E293B" if is_dark else "#F8FAFC"

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js"></script>
        <script src="https://www.gstatic.com/firebasejs/10.8.0/firebase-auth-compat.js"></script>
        <style>
            * {{
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }}
            body {{
                background: transparent;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            .google-btn {{
                width: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                background-color: {btn_bg};
                border: 1px solid {btn_border};
                border-radius: 8px;
                padding: 8px 14px;
                color: {btn_text};
                font-size: 13.5px;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
                height: 38px;
            }}
            .google-btn:hover {{
                background-color: {btn_hover_bg};
                border-color: #6366F1;
                transform: translateY(-1px);
                box-shadow: 0 2px 8px rgba(99, 102, 241, 0.15);
            }}
            .google-btn:disabled {{
                opacity: 0.7;
                cursor: not-allowed;
                transform: none !important;
            }}
            .google-icon {{
                width: 18px;
                height: 18px;
                flex-shrink: 0;
            }}
            .spinner-icon {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(99, 102, 241, 0.25);
                border-top: 2px solid #6366F1;
                border-radius: 50%;
                animation: spin 0.7s linear infinite;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .status-text {{
                font-size: 11px;
                color: {'#A5B4FC' if is_dark else '#6366F1'};
                margin-top: 3px;
                text-align: center;
                min-height: 14px;
                line-height: 1.2;
            }}
            .error-text {{
                color: #EF4444 !important;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <button class="google-btn" id="googleSignInBtn" onclick="handleRealGoogleSignIn()">
            <svg class="google-icon" id="btnIcon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
            </svg>
            <div class="spinner-icon" id="btnSpinner" style="display: none;"></div>
            <span id="btnLabel">{btn_text_label}</span>
        </button>
        <div id="statusMsg" class="status-text"></div>

        <script>
            const firebaseConfig = {fb_config_json};
            let isSigningIn = false;

            // Listen for popup auth messages from auth.html
            window.addEventListener("message", function(event) {{
                if (event.data && (event.data.type === "FIREBASE_AUTH_SUCCESS" || event.data.payload)) {{
                    const payload = event.data.payload;
                    const status = document.getElementById("statusMsg");
                    if (status && payload) {{
                        status.innerText = "Authenticated as " + (payload.name || payload.email) + "! Redirecting...";
                    }}
                    sendUserToStreamlit(payload);
                }}
            }});

            async function handleRealGoogleSignIn() {{
                if (isSigningIn) return;
                isSigningIn = true;

                const btn = document.getElementById("googleSignInBtn");
                const icon = document.getElementById("btnIcon");
                const spinner = document.getElementById("btnSpinner");
                const label = document.getElementById("btnLabel");
                const status = document.getElementById("statusMsg");

                btn.disabled = true;
                icon.style.display = "none";
                spinner.style.display = "inline-block";
                label.innerText = "Connecting to Google...";
                status.innerText = "Please complete sign-in in the Google popup...";

                try {{
                    // Try direct Firebase popup first
                    if (typeof firebase !== "undefined") {{
                        if (!firebase.apps.length) {{
                            firebase.initializeApp(firebaseConfig);
                        }}
                        const auth = firebase.auth();
                        const provider = new firebase.auth.GoogleAuthProvider();
                        provider.addScope('profile');
                        provider.addScope('email');
                        provider.setCustomParameters({{ prompt: 'select_account' }});

                        const result = await auth.signInWithPopup(provider);
                        const user = result.user;
                        
                        status.innerText = "Welcome " + (user.displayName || user.email) + "! Loading workspace...";
                        
                        const payload = {{
                            uid: user.uid,
                            name: user.displayName || user.email.split('@')[0],
                            email: user.email,
                            photo_url: user.photoURL || "",
                            provider: "google.com"
                        }};
                        
                        sendUserToStreamlit(payload);
                        return;
                    }} else {{
                        status.className = "status-text error-text";
                        status.innerText = "Firebase Auth SDK not loaded. Please try again.";
                        resetBtn();
                    }}
                }} catch(popupErr) {{
                    console.error("Firebase Google Auth error:", popupErr);
                    status.className = "status-text error-text";
                    
                    if (popupErr.code === "auth/unauthorized-domain") {{
                        status.innerText = "⚠️ Domain not authorized. Add 'data-studio-analyst15.streamlit.app' to Firebase Console > Authorized Domains.";
                    }} else if (popupErr.code === "auth/popup-blocked") {{
                        status.innerText = "⚠️ Popup was blocked by your browser. Please allow popups for this tab.";
                    }} else if (popupErr.code === "auth/popup-closed-by-user" || popupErr.code === "auth/cancelled-popup-request") {{
                        status.innerText = "Sign-in popup was closed.";
                    }} else if (popupErr.code === "auth/network-request-failed") {{
                        status.innerText = "Network error. Please check your internet connection.";
                    }} else {{
                        status.innerText = popupErr.message ? ("⚠️ " + popupErr.message) : "Failed to sign in with Google.";
                    }}
                    resetBtn();
                }}
            }}

            function resetBtn() {{
                isSigningIn = false;
                const btn = document.getElementById("googleSignInBtn");
                const icon = document.getElementById("btnIcon");
                const spinner = document.getElementById("btnSpinner");
                const label = document.getElementById("btnLabel");
                if (btn) btn.disabled = false;
                if (icon) icon.style.display = "inline-block";
                if (spinner) spinner.style.display = "none";
                if (label) label.innerText = "{btn_text_label}";
            }}

            function sendUserToStreamlit(userPayload) {{
                try {{
                    localStorage.setItem('ds_firebase_auth_user', JSON.stringify(userPayload));
                    sessionStorage.setItem('ds_firebase_auth_user', JSON.stringify(userPayload));
                }} catch(e) {{}}

                const jsonStr = JSON.stringify(userPayload);
                const b64 = btoa(unescape(encodeURIComponent(jsonStr)));

                try {{
                    window.parent.postMessage({{ type: "FIREBASE_AUTH_SUCCESS", payload: userPayload, fb_user: b64 }}, "*");
                }} catch(e) {{}}

                try {{
                    let parentHref = "";
                    try {{
                        if (window.top && window.top.location && window.top.location.href) {{
                            parentHref = window.top.location.href;
                        }}
                    }} catch(e) {{}}

                    if (!parentHref) {{
                        try {{
                            if (window.parent && window.parent.location && window.parent.location.href) {{
                                parentHref = window.parent.location.href;
                            }}
                        }} catch(e) {{}}
                    }}

                    if (!parentHref) {{
                        parentHref = document.referrer || window.location.href;
                    }}

                    const targetUrl = new URL(parentHref);
                    targetUrl.searchParams.set("fb_user", b64);

                    try {{
                        if (window.top) {{
                            window.top.location.href = targetUrl.toString();
                            return;
                        }}
                    }} catch(e) {{}}

                    window.location.href = targetUrl.toString();
                }} catch(navErr) {{
                    console.error("Navigation error:", navErr);
                }}
            }}
        </script>
    </body>
    </html>
    """
    components.html(html_code, height=68)


def render_account_sidebar_widget():
    """Render authenticated user information and Sign Out button inside sidebar."""
    user = get_current_user()

    if user:
        name = user.get("name", "User")
        email = user.get("email", "")
        photo_url = user.get("photo_url", "")
        provider = user.get("provider", "password")

        badge_bg = "#4285F4" if "google" in provider else ("#8B5CF6" if provider == "guest" else "#10B981")

        st.markdown(
            f"""
            <div class="sidebar-status-card" style="border-left: 3px solid {badge_bg}; padding: 0.65rem 0.75rem;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    {'<img src="' + photo_url + '" style="width: 34px; height: 34px; border-radius: 50%; object-fit: cover; border: 1.5px solid ' + badge_bg + ';" />' if photo_url else '<div style="width: 34px; height: 34px; border-radius: 50%; background: ' + badge_bg + '; color: white; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px;">' + name[0].upper() + '</div>'}
                    <div style="overflow: hidden; flex: 1;">
                        <div style="font-weight: 700; font-size: 0.85rem; color: var(--text-color, inherit); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{name}</div>
                        <div style="font-size: 0.72rem; color: #94A3B8; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{email}</div>
                    </div>
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
        if (window.firebase && firebase.apps.length) {
            firebase.auth().signOut().catch(e => console.debug(e));
        }
    } catch(e) {}
    </script>
    """
    components.html(clear_script, height=0, width=0)
    logout_user()
    st.rerun()
