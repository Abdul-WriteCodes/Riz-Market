# ============================================================
#  app.py — Entry point: config, routing, main()
#  All logic lives in dedicated modules.
# ============================================================

import streamlit as st
from styles import inject_styles, inject_sidebar_toggle
from sidebar import render_sidebar, check_access

# ── Page imports ──
from pages.page_login        import page_login
from pages.page_signup       import page_signup
from pages.page_pending      import page_pending_payment
from pages.page_forgot       import page_forgot_password
from pages.page_change_pw    import page_change_password
from pages.page_dashboard    import page_dashboard
from pages.page_record_sale  import page_record_sale
from pages.page_sales_history import page_sales_history
from pages.page_products     import page_products
from pages.page_expenses     import page_expenses
from pages.page_insights     import page_insights
from pages.page_admin        import page_admin

# ── Streamlit page config (must be first st call) ──
st.set_page_config(
    page_title="BizPulse — SME Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    inject_styles()
    inject_sidebar_toggle()

    # ── Auth gate ──
    if "user" not in st.session_state:
        st.session_state.user = None

    user = st.session_state.user

    # ── Unauthenticated routes ──
    if user is None:
        page = st.session_state.get("auth_page", "login")
        if   page == "login":   page_login()
        elif page == "signup":  page_signup()
        elif page == "forgot":  page_forgot_password()
        return

    # ── Force password change if flagged ──
    if user.get("must_change_password") == "yes":
        page_change_password(forced=True)
        return

    # ── Pending payment gate ──
    if user.get("plan_status") == "pending_payment":
        page_pending_payment()
        return

    # ── Render sidebar for authenticated users ──
    render_sidebar()

    # ── Access check (subscription expired etc.) ──
    if not check_access():
        return

    # ── Main router ──
    page = st.session_state.get("current_page", "dashboard")

    if   page == "dashboard":       page_dashboard()
    elif page == "record_sale":     page_record_sale()
    elif page == "sales_history":   page_sales_history()
    elif page == "products":        page_products()
    elif page == "expenses":        page_expenses()
    elif page == "insights":        page_insights()
    elif page == "admin":           page_admin()
    elif page == "change_password": page_change_password(forced=False)
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
