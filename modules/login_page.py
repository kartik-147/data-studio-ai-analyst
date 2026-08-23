"""
Authentication and Product Landing Page for Data Studio
Hand-crafted Linear/Mixpanel SaaS aesthetic:
- Precision vector iconography (Lucide SVGs)
- Clean typography and type scale
- Focused, friction-free authentication
- Full light/dark mode support
"""

import re
import streamlit as st
from modules.config import (
    APP_NAME,
)
from modules.auth import (
    authenticate_user,
    register_user,
    authenticate_google_user,
    login_user,
)
from modules.ui_components import render_theme_toggle_button, render_html
from modules.icons import icon_svg


def _is_valid_email(email: str) -> bool:
    """Validate email format."""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email.strip()))


def render_login_page():
    """Render the polished Linear/Mixpanel style authentication page."""
    theme = st.session_state.get("theme", "light")
    is_dark = theme == "dark"

    # Inject Page-Specific Polish CSS
    auth_css = f"""
    <style>
    html, body, [data-testid="stAppViewContainer"], .stApp {{
        overflow-y: auto !important;
        min-height: 100vh !important;
        background-color: {'#0B0F17' if is_dark else '#F8FAFC'} !important;
        background-image: {'radial-gradient(circle at 12% 88%, rgba(37, 99, 235, 0.12) 0%, transparent 40%), radial-gradient(circle at 88% 12%, rgba(79, 70, 229, 0.10) 0%, transparent 40%)' if is_dark else 'radial-gradient(circle at 10% 90%, rgba(219, 234, 254, 0.55) 0%, transparent 35%), radial-gradient(circle at 90% 10%, rgba(224, 231, 255, 0.45) 0%, transparent 35%)'} !important;
    }}

    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 960px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: flex-start !important;
    }}

    header[data-testid="stHeader"], .stAppHeader {{
        display: none !important;
    }}

    .brand-header-left {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}

    .brand-logo-badge {{
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: {'#1E293B' if is_dark else '#EFF6FF'};
        border: 1px solid {'#334155' if is_dark else '#DBEAFE'};
        display: flex;
        align-items: center;
        justify-content: center;
        color: #3B82F6;
    }}

    .brand-title-text {{
        font-size: 1.15rem;
        font-weight: 700;
        color: {'#F8FAFC' if is_dark else '#0F172A'};
        letter-spacing: -0.02em;
        font-family: var(--font-heading);
    }}

    .hero-container {{
        text-align: center;
        margin-top: 0.35rem;
        margin-bottom: 0.85rem;
    }}

    .hero-headline {{
        font-size: 2.1rem;
        font-weight: 800;
        color: {'#F8FAFC' if is_dark else '#0F172A'};
        letter-spacing: -0.03em;
        line-height: 1.2;
        margin: 0 0 0.35rem 0;
        font-family: var(--font-heading);
    }}

    .hero-dot {{
        color: #3B82F6;
    }}

    .hero-subtitle {{
        font-size: 0.88rem;
        color: {'#94A3B8' if is_dark else '#64748B'};
        line-height: 1.5;
        max-width: 560px;
        margin: 0 auto;
    }}

    .feature-card-item {{
        background: {'#111827' if is_dark else '#FFFFFF'};
        border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'};
        border-radius: 8px;
        padding: 10px 12px;
        height: 100%;
        display: flex;
        align-items: flex-start;
        gap: 10px;
        transition: border-color 0.15s ease;
    }}

    .feature-card-item:hover {{
        border-color: {'#3B82F6' if is_dark else '#93C5FD'};
    }}

    .feature-icon-box {{
        width: 32px;
        height: 32px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
    }}

    .feature-title-text {{
        font-size: 0.82rem;
        font-weight: 600;
        color: {'#F8FAFC' if is_dark else '#0F172A'};
        margin-bottom: 2px;
        line-height: 1.2;
    }}

    .feature-desc-text {{
        font-size: 0.72rem;
        color: {'#94A3B8' if is_dark else '#64748B'};
        line-height: 1.35;
    }}

    .auth-section-wrapper {{
        margin-top: 0.65rem;
        text-align: center;
    }}

    .auth-heading {{
        font-size: 1.25rem;
        font-weight: 700;
        color: {'#F8FAFC' if is_dark else '#0F172A'};
        margin: 0 0 2px 0;
        font-family: var(--font-heading);
    }}

    .auth-subheading {{
        font-size: 0.8rem;
        color: {'#94A3B8' if is_dark else '#64748B'};
        margin: 0 0 10px 0;
    }}

    .stTextInput > div > div > input {{
        background-color: {'#111827' if is_dark else '#FFFFFF'} !important;
        border: 1px solid {'#334155' if is_dark else '#CBD5E1'} !important;
        border-radius: 6px !important;
        padding: 0.35rem 0.75rem !important;
        font-size: 0.84rem !important;
        height: 36px !important;
        color: {'#F8FAFC' if is_dark else '#0F172A'} !important;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.2) !important;
    }}

    .stTextInput label {{
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        color: {'#CBD5E1' if is_dark else '#475569'} !important;
        margin-bottom: 0.15rem !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}

    div[data-testid="stForm"] {{
        border: none !important;
        padding: 0 !important;
    }}

    div[data-testid="stForm"] .stButton button {{
        background: #2563EB !important;
        color: #FFFFFF !important;
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        border: none !important;
        border-radius: 6px !important;
        height: 36px !important;
        box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3) !important;
        margin-top: 0.25rem !important;
    }}

    div[data-testid="stForm"] .stButton button:hover {{
        background: #1D4ED8 !important;
        transform: translateY(-1px) !important;
    }}

    .bottom-action-btn .stButton button {{
        background: {'#111827' if is_dark else '#FFFFFF'} !important;
        border: 1px solid {'#1E293B' if is_dark else '#E2E8F0'} !important;
        color: {'#94A3B8' if is_dark else '#475569'} !important;
        border-radius: 6px !important;
        font-size: 0.76rem !important;
        font-weight: 500 !important;
        height: 32px !important;
    }}

    .bottom-action-btn .stButton button:hover {{
        border-color: #2563EB !important;
        color: #2563EB !important;
    }}
    </style>
    """
    st.markdown(auth_css, unsafe_allow_html=True)

    # 1. Top Header Bar
    top_c1, top_c2 = st.columns([5.2, 1.2])
    with top_c1:
        render_html(
            f"""
            <div class="brand-header-left">
                <div class="brand-logo-badge">
                    {icon_svg("activity", size=18, color="#3B82F6", stroke=2.2)}
                </div>
                <span class="brand-title-text">{APP_NAME}</span>
            </div>
            """
        )
    with top_c2:
        render_theme_toggle_button(key_suffix="auth_header")

    # 2. Hero Header
    render_html(
        """
        <div class="hero-container">
            <h1 class="hero-headline">Exploratory Data Analysis Workbench<span class="hero-dot">.</span></h1>
            <p class="hero-subtitle">
                Automated profiling, statistical quality audits, interactive visualization, and targeted analytical workflows.
            </p>
        </div>
        """
    )

    # 3. Four Feature Cards with Clean Vector SVGs
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        render_html(
            f"""
            <div class="feature-card-item">
                <div class="feature-icon-box" style="background: {'rgba(37, 99, 235, 0.15)' if is_dark else '#EFF6FF'}; color: #2563EB;">
                    {icon_svg("database", size=16, color="#2563EB")}
                </div>
                <div class="feature-text-box">
                    <div class="feature-title-text">Dataset Profiling</div>
                    <div class="feature-desc-text">Schema inspection, null auditing, and type classification.</div>
                </div>
            </div>
            """
        )

    with c2:
        render_html(
            f"""
            <div class="feature-card-item">
                <div class="feature-icon-box" style="background: {'rgba(16, 185, 129, 0.15)' if is_dark else '#ECFDF5'}; color: #059669;">
                    {icon_svg("shield-check", size=16, color="#059669")}
                </div>
                <div class="feature-text-box">
                    <div class="feature-title-text">Quality Scoring</div>
                    <div class="feature-desc-text">Composite health rating across completeness and uniqueness.</div>
                </div>
            </div>
            """
        )

    with c3:
        render_html(
            f"""
            <div class="feature-card-item">
                <div class="feature-icon-box" style="background: {'rgba(79, 70, 229, 0.15)' if is_dark else '#EEF2FF'}; color: #4F46E5;">
                    {icon_svg("bar-chart-2", size=16, color="#4F46E5")}
                </div>
                <div class="feature-text-box">
                    <div class="feature-title-text">Visual Analytics</div>
                    <div class="feature-desc-text">Correlation heatmaps, distribution grids, and outliers.</div>
                </div>
            </div>
            """
        )

    with c4:
        render_html(
            f"""
            <div class="feature-card-item">
                <div class="feature-icon-box" style="background: {'rgba(245, 158, 11, 0.15)' if is_dark else '#FFFBEB'}; color: #D97706;">
                    {icon_svg("cpu", size=16, color="#D97706")}
                </div>
                <div class="feature-text-box">
                    <div class="feature-title-text">Automated Insights</div>
                    <div class="feature-desc-text">Natural language querying and smart analytical summaries.</div>
                </div>
            </div>
            """
        )

    # 4. Authentication Card
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "signin"

    is_signup = st.session_state.auth_mode == "signup"

    _, auth_center, _ = st.columns([1, 1.35, 1])

    with auth_center:
        render_html(
            f"""
            <div class="auth-section-wrapper">
                <h2 class="auth-heading">{'Create Your Account' if is_signup else 'Welcome to Data Studio'}</h2>
                <p class="auth-subheading">{'Sign up to access your analytics workspace.' if is_signup else 'Sign in to access your analytics workspace.'}</p>
            </div>
            """
        )

        if not is_signup:
            auth_tab_google, auth_tab_email = st.tabs(["Google Account", "Email & Password"])

            with auth_tab_google:
                render_html(
                    f"""
                    <div style="background: {'rgba(37, 99, 235, 0.08)' if is_dark else '#F0F7FF'}; border: 1px solid {'#1E3A8A' if is_dark else '#BFDBFE'}; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                        <svg viewBox="0 0 24 24" width="22" height="22" style="flex-shrink: 0;">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        <div style="font-size: 0.78rem; color: {'#93C5FD' if is_dark else '#1E40AF'}; line-height: 1.35;">
                            Fast, secure sign-in with your Google or Workspace account.
                        </div>
                    </div>
                    """
                )
                with st.form("form_google_signin", clear_on_submit=False):
                    google_email_val = st.text_input(
                        "Google Account Email",
                        placeholder="e.g. name@gmail.com or company email",
                        key="google_auth_email_input",
                    )
                    submit_google = st.form_submit_button("Continue with Google", use_container_width=True)

                if submit_google:
                    clean_gemail = google_email_val.strip() if google_email_val else ""
                    if not clean_gemail:
                        st.error("Please enter your Google or Gmail account email.")
                    else:
                        success, msg, user_data = authenticate_google_user(clean_gemail)
                        if success and user_data:
                            login_user(user_data)
                            st.rerun()
                        else:
                            st.error(msg)

            with auth_tab_email:
                with st.form("form_exact_signin", clear_on_submit=False):
                    email_val = st.text_input("Email or Username", placeholder="name@company.com or username", key="auth_in_email")
                    pwd_val = st.text_input("Password", type="password", placeholder="Enter your password", key="auth_in_pwd")
                    submit_signin = st.form_submit_button("Sign In", use_container_width=True)

                if submit_signin:
                    clean_email = email_val.strip() if email_val else ""
                    clean_pwd = pwd_val if pwd_val else ""
                    if not clean_email:
                        st.error("Please enter your email or username.")
                    elif not clean_pwd:
                        st.error("Please enter your password.")
                    else:
                        success, msg, user_data = authenticate_user(clean_email, clean_pwd)
                        if success and user_data:
                            login_user(user_data)
                            st.rerun()
                        else:
                            st.error(msg)

            st.write("")
            b_col1, b_col2 = st.columns([1.6, 1.2])
            with b_col1:
                st.markdown('<div class="bottom-action-btn">', unsafe_allow_html=True)
                if st.button("Create Account", key="auth_btn_signup", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            with b_col2:
                st.markdown('<div class="bottom-action-btn">', unsafe_allow_html=True)
                if st.button("Guest Access", key="auth_btn_guest", use_container_width=True):
                    login_user({
                        "uid": "guest-analyst-001",
                        "name": "Guest Analyst",
                        "email": "guest@datastudiokb.local",
                        "photo_url": "",
                        "provider": "guest",
                    })
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        else:
            auth_tab_reg_google, auth_tab_reg_email = st.tabs(["Sign Up with Google", "Standard Sign Up"])

            with auth_tab_reg_google:
                render_html(
                    f"""
                    <div style="background: {'rgba(37, 99, 235, 0.08)' if is_dark else '#F0F7FF'}; border: 1px solid {'#1E3A8A' if is_dark else '#BFDBFE'}; border-radius: 8px; padding: 12px 14px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                        <svg viewBox="0 0 24 24" width="22" height="22" style="flex-shrink: 0;">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                        </svg>
                        <div style="font-size: 0.78rem; color: {'#93C5FD' if is_dark else '#1E40AF'}; line-height: 1.35;">
                            Create your analytics workspace with your Google Account.
                        </div>
                    </div>
                    """
                )
                with st.form("form_google_signup", clear_on_submit=False):
                    greg_name = st.text_input("Your Name", placeholder="e.g. Alex Johnson", key="google_reg_name")
                    greg_email = st.text_input("Google Email Address", placeholder="name@gmail.com", key="google_reg_email")
                    submit_greg = st.form_submit_button("Sign up with Google", use_container_width=True)

                if submit_greg:
                    clean_gname = greg_name.strip() if greg_name else ""
                    clean_gemail = greg_email.strip() if greg_email else ""
                    if not clean_gemail:
                        st.error("Please enter your Google Email address.")
                    else:
                        success, msg, user_data = authenticate_google_user(clean_gemail, name=clean_gname)
                        if success and user_data:
                            login_user(user_data)
                            st.rerun()
                        else:
                            st.error(msg)

            with auth_tab_reg_email:
                with st.form("form_exact_signup", clear_on_submit=False):
                    name_val = st.text_input("Full Name", placeholder="e.g. Alex Johnson", key="auth_reg_name")
                    email_val = st.text_input("Email Address", placeholder="name@company.com", key="auth_reg_email")
                    pwd_val = st.text_input("Password", type="password", placeholder="Minimum 6 characters", key="auth_reg_pwd")
                    submit_signup = st.form_submit_button("Create Account", use_container_width=True)

                if submit_signup:
                    clean_name = name_val.strip() if name_val else ""
                    clean_email = email_val.strip() if email_val else ""
                    clean_pwd = pwd_val if pwd_val else ""
                    
                    if not clean_name:
                        st.error("Please enter your full name.")
                    elif not clean_email:
                        st.error("Please enter your email address.")
                    elif not clean_pwd or len(clean_pwd) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        success, msg, user_data = register_user(clean_name, clean_email, clean_pwd)
                        if success and user_data:
                            login_user(user_data)
                            st.rerun()
                        else:
                            st.error(msg)

            st.write("")
            st.markdown('<div class="bottom-action-btn">', unsafe_allow_html=True)
            if st.button("Back to Sign In", key="auth_btn_signin", use_container_width=True):
                st.session_state.auth_mode = "signin"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
