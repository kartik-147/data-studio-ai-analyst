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
    login_user,
)
from modules.auth import render_google_sign_in_component
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
        overflow: hidden !important;
        height: 100vh !important;
        max-height: 100vh !important;
        background-color: {'#0B0F17' if is_dark else '#F8FAFC'} !important;
        background-image: {'radial-gradient(circle at 12% 88%, rgba(37, 99, 235, 0.12) 0%, transparent 40%), radial-gradient(circle at 88% 12%, rgba(79, 70, 229, 0.10) 0%, transparent 40%)' if is_dark else 'radial-gradient(circle at 10% 90%, rgba(219, 234, 254, 0.55) 0%, transparent 35%), radial-gradient(circle at 90% 10%, rgba(224, 231, 255, 0.45) 0%, transparent 35%)'} !important;
    }}

    .block-container {{
        padding-top: 0.75rem !important;
        padding-bottom: 0.75rem !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        max-width: 960px !important;
        height: 100vh !important;
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
            with st.form("form_exact_signin", clear_on_submit=False):
                email_val = st.text_input("Email", placeholder="name@company.com or username", key="auth_in_email")
                pwd_val = st.text_input("Password", type="password", placeholder="Enter your password", key="auth_in_pwd")
                submit_signin = st.form_submit_button("Sign In", use_container_width=True)

            if submit_signin:
                clean_email = email_val.strip() if email_val else ""
                if not clean_email:
                    st.error("Please enter your email or username.")
                else:
                    display_name = clean_email.split("@")[0].capitalize() if "@" in clean_email else clean_email.capitalize()
                    user_email = clean_email if "@" in clean_email else f"{clean_email.lower()}@datastudiokb.local"
                    login_user({
                        "uid": f"usr-{abs(hash(clean_email)) % 1000000}",
                        "name": display_name,
                        "email": user_email,
                        "photo_url": "",
                        "provider": "password",
                    })
                    st.rerun()

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
            with st.form("form_exact_signup", clear_on_submit=False):
                name_val = st.text_input("Full Name", placeholder="e.g. Alex Johnson", key="auth_reg_name")
                email_val = st.text_input("Email Address", placeholder="name@company.com", key="auth_reg_email")
                pwd_val = st.text_input("Password", type="password", placeholder="Minimum 6 characters", key="auth_reg_pwd")
                submit_signup = st.form_submit_button("Create Account", use_container_width=True)

            if submit_signup:
                clean_name = name_val.strip() if name_val else ""
                clean_email = email_val.strip() if email_val else ""
                
                if not clean_name:
                    st.error("Please enter your full name.")
                elif not clean_email:
                    st.error("Please enter your email address.")
                else:
                    login_user({
                        "uid": f"usr-reg-{abs(hash(clean_email)) % 1000000}",
                        "name": clean_name,
                        "email": clean_email,
                        "photo_url": "",
                        "provider": "password",
                    })
                    st.rerun()

            st.markdown('<div class="bottom-action-btn">', unsafe_allow_html=True)
            if st.button("Back to Sign In", key="auth_btn_signin", use_container_width=True):
                st.session_state.auth_mode = "signin"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
