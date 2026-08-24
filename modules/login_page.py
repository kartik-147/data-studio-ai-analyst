"""
Authentication and Product Landing Page for Data Studio
========================================================
Hand-crafted Linear/Mixpanel SaaS aesthetic:
- One-click Real Google OAuth / OpenID Connect
- Verified Email & Password Authentication (bcrypt)
- Isolated Guest Demo Mode
- Full light/dark mode support
"""

import streamlit as st
from modules.config import APP_NAME
from modules.auth import (
    authenticate_user,
    create_user,
    login_user,
    login_guest_user,
)
from modules.ui_components import render_theme_toggle_button, render_html
from modules.icons import icon_svg


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

    /* High-contrast tab headers for authentication */
    div[data-testid="stTabs"] button[role="tab"] {{
        font-size: 0.86rem !important;
        font-weight: 600 !important;
        color: {'#94A3B8' if is_dark else '#64748B'} !important;
    }}

    div[data-testid="stTabs"] button[aria-selected="true"] {{
        color: {'#3B82F6' if is_dark else '#2563EB'} !important;
        border-bottom-color: #2563EB !important;
    }}

    .auth-banner-box {{
        background: {'rgba(37, 99, 235, 0.08)' if is_dark else '#F0F7FF'};
        border: 1px solid {'#1E3A8A' if is_dark else '#BFDBFE'};
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 10px;
    }}

    .google-btn-wrapper .stButton button {{
        background: {'#111827' if is_dark else '#FFFFFF'} !important;
        border: 1px solid {'#334155' if is_dark else '#CBD5E1'} !important;
        color: {'#F8FAFC' if is_dark else '#1E293B'} !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        height: 40px !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 8px !important;
        transition: all 0.15s ease !important;
    }}

    .google-btn-wrapper .stButton button:hover {{
        border-color: #4285F4 !important;
        background: {'#1E293B' if is_dark else '#F8FAFC'} !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(66, 133, 244, 0.15) !important;
    }}

    .guest-btn-wrapper .stButton button {{
        background: transparent !important;
        border: 1px dashed {'#334155' if is_dark else '#CBD5E1'} !important;
        color: {'#94A3B8' if is_dark else '#64748B'} !important;
        font-weight: 500 !important;
        font-size: 0.80rem !important;
        height: 34px !important;
        border-radius: 6px !important;
        transition: all 0.15s ease !important;
    }}

    .guest-btn-wrapper .stButton button:hover {{
        border-color: #8B5CF6 !important;
        color: #8B5CF6 !important;
        background: {'rgba(139, 92, 246, 0.06)' if is_dark else '#F5F3FF'} !important;
    }}

    .auth-separator {{
        display: flex;
        align-items: center;
        margin: 14px 0 12px 0;
        text-align: center;
    }}

    .auth-separator::before, .auth-separator::after {{
        content: '';
        flex: 1;
        border-bottom: 1px solid {'#1E293B' if is_dark else '#E2E8F0'};
    }}

    .auth-separator span {{
        padding: 0 10px;
        font-size: 0.70rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: {'#64748B' if is_dark else '#94A3B8'};
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

    # 4. Authentication Container
    _, auth_center, _ = st.columns([1, 1.35, 1])

    with auth_center:
        render_html(
            f"""
            <div class="auth-section-wrapper">
                <h2 class="auth-heading">Authentication & Workspace Access</h2>
                <p class="auth-subheading">Sign in with your Email credentials or explore with Guest Demo.</p>
            </div>
            """
        )

        # ----------------------------------------------------------------------
        # EMAIL & PASSWORD TABS
        # ----------------------------------------------------------------------
        tab_signin, tab_signup = st.tabs(["Sign In", "Create Account"])

        # TAB 1: SECURE SIGN IN
        with tab_signin:
            render_html(
                f"""
                <div class="auth-banner-box">
                    {icon_svg("lock", size=16, color="#3B82F6")}
                    <div style="font-size: 0.78rem; color: {'#93C5FD' if is_dark else '#1E40AF'}; line-height: 1.35;">
                        Enter your registered email address and password to access your workspace.
                    </div>
                </div>
                """
            )

            with st.form("form_secure_signin", clear_on_submit=False):
                email_val = st.text_input(
                    "Email Address",
                    placeholder="name@company.com",
                    key="auth_in_email",
                )
                pwd_val = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Enter your password",
                    key="auth_in_pwd",
                )
                submit_signin = st.form_submit_button("Sign In to Data Studio", use_container_width=True)

            if submit_signin:
                clean_email = email_val.strip() if email_val else ""
                clean_pwd = pwd_val if pwd_val else ""

                if not clean_email:
                    st.error("Please enter your email address.")
                elif not clean_pwd:
                    st.error("Please enter your password.")
                else:
                    success, msg, user_data = authenticate_user(clean_email, clean_pwd)
                    if success and user_data:
                        login_user(user_data)
                        st.rerun()
                    else:
                        st.error(msg)

        # TAB 2: CREATE NEW ACCOUNT
        with tab_signup:
            render_html(
                f"""
                <div class="auth-banner-box">
                    {icon_svg("user-plus", size=16, color="#10B981")}
                    <div style="font-size: 0.78rem; color: {'#A7F3D0' if is_dark else '#065F46'}; line-height: 1.35;">
                        Register your account with secure bcrypt password hashing and workspace history.
                    </div>
                </div>
                """
            )

            with st.form("form_secure_signup", clear_on_submit=False):
                reg_name = st.text_input(
                    "Full Name",
                    placeholder="e.g. Alex Johnson",
                    key="auth_reg_name",
                )
                reg_email = st.text_input(
                    "Email Address",
                    placeholder="name@company.com",
                    key="auth_reg_email",
                )
                reg_pwd = st.text_input(
                    "Password",
                    type="password",
                    placeholder="Minimum 6 characters",
                    key="auth_reg_pwd",
                )
                reg_pwd_confirm = st.text_input(
                    "Confirm Password",
                    type="password",
                    placeholder="Re-type your password",
                    key="auth_reg_pwd_confirm",
                )
                submit_signup = st.form_submit_button("Create Account & Access Workspace", use_container_width=True)

            if submit_signup:
                clean_name = reg_name.strip() if reg_name else ""
                clean_email = reg_email.strip() if reg_email else ""
                clean_pwd = reg_pwd if reg_pwd else ""
                clean_confirm = reg_pwd_confirm if reg_pwd_confirm else ""

                if not clean_name:
                    st.error("Please enter your full name.")
                elif not clean_email:
                    st.error("Please enter your email address.")
                elif not clean_pwd or len(clean_pwd) < 6:
                    st.error("Password must be at least 6 characters long.")
                elif clean_pwd != clean_confirm:
                    st.error("Passwords do not match. Please ensure both passwords match.")
                else:
                    success, msg, user_data = create_user(clean_name, clean_email, clean_pwd, clean_confirm)
                    if success and user_data:
                        login_user(user_data)
                        st.success("Account created successfully! Entering workspace...")
                        st.rerun()
                    else:
                        st.error(msg)

        # ----------------------------------------------------------------------
        # C. GUEST DEMO ACCESS (Separate Option)
        # ----------------------------------------------------------------------
        st.write("")
        st.markdown('<div class="guest-btn-wrapper">', unsafe_allow_html=True)
        if st.button("🚀 Explore as Guest Demo", key="auth_btn_guest_demo", use_container_width=True):
            login_guest_user()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
