# ============================================================
#  SME DASHBOARD — app.py
#  Lightweight Business Intelligence SaaS for SMEs
#  Stack: Streamlit · Google Sheets · Plotly · Pandas
# ============================================================

import streamlit as st
import gspread
import bcrypt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import uuid
import re
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from google.oauth2.service_account import Credentials

# ─────────────────────────────────────────────
#  APP CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="BizPulse — SME Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet tab names
SHEET_USERS    = "USERS"
SHEET_PRODUCTS = "PRODUCTS"
SHEET_SALES    = "SALES"
SHEET_EXPENSES = "EXPENSES"

# Payment details (update to your real account)
PAYMENT_DETAILS = {
    "bank":          "Your Bank Name",
    "account_name":  "Your Business Name",
    "account_number":"0000000000",
    "monthly_price": 1000,
    "yearly_price":  10000,
    "trial_days":    14,
}

# Admin credentials from secrets
ADMIN_EMAIL    = st.secrets["admin"]["email"]
ADMIN_PASSWORD = st.secrets["admin"]["password"]
ADMIN_BIZ_ID   = st.secrets["admin"]["business_id"]


# ─────────────────────────────────────────────
#  GLOBAL STYLES
# ─────────────────────────────────────────────
def inject_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    /* Hide default Streamlit elements */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }

    /* ── KPI Cards ── */
    .kpi-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        color: white;
        margin-bottom: 1rem;
    }
    .kpi-label {
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94a3b8;
        margin-bottom: 0.4rem;
    }
    .kpi-value {
        font-size: 1.9rem;
        font-weight: 800;
        color: #f1f5f9;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1.1;
    }
    .kpi-sub {
        font-size: 0.78rem;
        color: #64748b;
        margin-top: 0.35rem;
    }
    .kpi-positive { color: #34d399; }
    .kpi-negative { color: #f87171; }

    /* ── Alert Cards ── */
    .alert-low {
        background: #fef3c7; border-left: 4px solid #f59e0b;
        border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
        color: #92400e; font-size: 0.85rem;
    }
    .alert-critical {
        background: #fee2e2; border-left: 4px solid #ef4444;
        border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
        color: #991b1b; font-size: 0.85rem;
    }
    .alert-success {
        background: #d1fae5; border-left: 4px solid #10b981;
        border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem;
        color: #065f46; font-size: 0.85rem;
    }

    /* ── Section Headers ── */
    .section-header {
        font-size: 1.1rem; font-weight: 700;
        color: #1e293b; margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #e2e8f0;
    }

    /* ── Page Title ── */
    .page-title {
        font-size: 1.75rem; font-weight: 800;
        color: #0f172a; margin-bottom: 0.25rem;
    }
    .page-subtitle {
        font-size: 0.9rem; color: #64748b;
        margin-bottom: 1.5rem;
    }

    /* ── Auth Card ── */
    .auth-card {
        max-width: 480px; margin: 2rem auto;
        background: white; border-radius: 20px;
        padding: 2.5rem; box-shadow: 0 20px 60px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    .auth-logo {
        font-size: 2rem; font-weight: 800; color: #0f172a;
        text-align: center; margin-bottom: 0.25rem;
    }
    .auth-tagline {
        text-align: center; color: #64748b;
        font-size: 0.875rem; margin-bottom: 2rem;
    }

    /* ── Plan Cards ── */
    .plan-card {
        border: 2px solid #e2e8f0; border-radius: 12px;
        padding: 1.25rem; text-align: center; cursor: pointer;
        transition: all 0.2s; margin-bottom: 0.5rem;
    }
    .plan-card:hover { border-color: #6366f1; }
    .plan-selected { border-color: #6366f1 !important; background: #eef2ff; }
    .plan-badge {
        background: #6366f1; color: white; font-size: 0.65rem;
        font-weight: 700; padding: 2px 8px; border-radius: 99px;
        text-transform: uppercase; letter-spacing: 0.05em;
    }

    /* ── Stock Status Pills ── */
    .stock-ok    { background:#d1fae5; color:#065f46; padding:3px 10px; border-radius:99px; font-size:0.75rem; font-weight:600; }
    .stock-low   { background:#fef3c7; color:#92400e; padding:3px 10px; border-radius:99px; font-size:0.75rem; font-weight:600; }
    .stock-critical { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:99px; font-size:0.75rem; font-weight:600; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: 10px; font-weight: 600;
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1, #4f46e5);
        border: none; color: white;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  GOOGLE SHEETS SERVICE LAYER
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_gspread_client():
    """Authenticate and return gspread client. Cached for performance."""
    creds_dict = dict(st.secrets["google_credentials"])
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)


def get_sheet(tab_name: str):
    """Return a specific worksheet by tab name."""
    client   = get_gspread_client()
    sheet_id = st.secrets["google_sheets"]["sheet_id"]
    book     = client.open_by_key(sheet_id)
    return book.worksheet(tab_name)


def read_sheet(tab_name: str) -> pd.DataFrame:
    """Read entire sheet tab into a DataFrame."""
    try:
        ws      = get_sheet(tab_name)
        records = ws.get_all_records()
        return pd.DataFrame(records) if records else pd.DataFrame()
    except Exception as e:
        st.error(f"Error reading {tab_name}: {e}")
        return pd.DataFrame()


def append_row(tab_name: str, row: list):
    """Append a single row to a sheet tab."""
    try:
        ws = get_sheet(tab_name)
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.error(f"Error writing to {tab_name}: {e}")
        return False


def update_row(tab_name: str, row_index: int, col_index: int, value):
    """Update a single cell. row_index and col_index are 1-based."""
    try:
        ws = get_sheet(tab_name)
        ws.update_cell(row_index, col_index, value)
        return True
    except Exception as e:
        st.error(f"Error updating {tab_name}: {e}")
        return False


def update_row_by_id(tab_name: str, id_col: str, id_val: str, updates: dict):
    """
    Find a row where id_col == id_val and update multiple columns.
    updates = {"column_name": new_value, ...}
    """
    try:
        ws      = get_sheet(tab_name)
        records = ws.get_all_records()
        headers = ws.row_values(1)

        for i, rec in enumerate(records):
            if str(rec.get(id_col)) == str(id_val):
                row_num = i + 2  # +1 for header, +1 for 1-based index
                for col_name, new_val in updates.items():
                    if col_name in headers:
                        col_num = headers.index(col_name) + 1
                        ws.update_cell(row_num, col_num, new_val)
                return True
        return False
    except Exception as e:
        st.error(f"Error updating row in {tab_name}: {e}")
        return False


def delete_row_by_id(tab_name: str, id_col: str, id_val: str) -> bool:
    """Delete a row where id_col == id_val."""
    try:
        ws      = get_sheet(tab_name)
        records = ws.get_all_records()
        for i, rec in enumerate(records):
            if str(rec.get(id_col)) == str(id_val):
                ws.delete_rows(i + 2)
                return True
        return False
    except Exception as e:
        st.error(f"Error deleting from {tab_name}: {e}")
        return False


# ─────────────────────────────────────────────
#  UTILITY HELPERS
# ─────────────────────────────────────────────

def gen_id(prefix=""):
    """Generate a short unique ID."""
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


def fmt_naira(amount):
    """Format a number as Nigerian Naira."""
    try:
        return f"₦{float(amount):,.2f}"
    except:
        return "₦0.00"


def safe_float(val, default=0.0):
    try:
        return float(val)
    except:
        return default


def safe_int(val, default=0):
    try:
        return int(val)
    except:
        return default


def parse_date(val):
    """Parse a date string to datetime, return None on failure."""
    try:
        return dateparser.parse(str(val))
    except:
        return None


def validate_email(email: str) -> bool:
    return bool(re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email))


# ─────────────────────────────────────────────
#  AUTH FUNCTIONS
# ─────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def check_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except:
        return False


def get_user_by_email(email: str):
    """Return user dict or None."""
    df = read_sheet(SHEET_USERS)
    if df.empty:
        return None
    match = df[df["email"].str.lower() == email.lower()]
    return match.iloc[0].to_dict() if not match.empty else None


def is_subscription_active(user: dict) -> bool:
    """Check if user has active, non-expired subscription."""
    if user.get("plan_status") != "active":
        return False
    end = parse_date(user.get("subscription_end", ""))
    if end is None:
        return False
    return datetime.now() <= end


def login_user(email: str, password: str):
    """
    Validate credentials. Returns (success, user_dict, message).
    Handles admin login separately.
    """
    # Admin shortcut
    if email.lower() == ADMIN_EMAIL.lower() and password == ADMIN_PASSWORD:
        admin_user = {
            "user_id":      "ADMIN",
            "business_id":  ADMIN_BIZ_ID,
            "business_name":"BizPulse Admin",
            "full_name":    "Administrator",
            "email":        ADMIN_EMAIL,
            "role":         "admin",
            "plan_status":  "active",
            "subscription_end": (datetime.now() + timedelta(days=3650)).strftime("%Y-%m-%d"),
        }
        return True, admin_user, "Welcome, Admin!"

    user = get_user_by_email(email)
    if not user:
        return False, None, "No account found with that email."
    if not check_password(password, str(user.get("password_hash", ""))):
        return False, None, "Incorrect password."
    return True, user, "Login successful."


def signup_user(business_name, full_name, email, password, plan_type):
    """
    Create a new user. Returns (success, message).
    Trial → active immediately. Paid plans → pending_payment.
    """
    if not validate_email(email):
        return False, "Please enter a valid email address."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    if get_user_by_email(email):
        return False, "An account with this email already exists."

    user_id     = gen_id("USR")
    business_id = gen_id("BIZ")
    now         = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if plan_type == "trial":
        status = "active"
        start  = datetime.now().strftime("%Y-%m-%d")
        end    = (datetime.now() + timedelta(days=PAYMENT_DETAILS["trial_days"])).strftime("%Y-%m-%d")
    else:
        status = "pending_payment"
        start  = ""
        end    = ""

    row = [
        user_id, business_id, business_name, full_name, email,
        hash_password(password), "owner", plan_type,
        status, start, end, now
    ]
    success = append_row(SHEET_USERS, row)
    if success:
        return True, "Account created successfully."
    return False, "Failed to create account. Please try again."


# ─────────────────────────────────────────────
#  ANALYTICS FUNCTIONS
# ─────────────────────────────────────────────

def get_sales_df(business_id: str) -> pd.DataFrame:
    """Return sales DataFrame filtered to this business, with typed columns."""
    df = read_sheet(SHEET_SALES)
    if df.empty:
        return pd.DataFrame()
    df = df[df["business_id"] == business_id].copy()
    if df.empty:
        return df
    df["sale_date"]    = pd.to_datetime(df["sale_date"], errors="coerce")
    df["total_amount"] = pd.to_numeric(df["total_amount"], errors="coerce").fillna(0)
    df["gross_profit"] = pd.to_numeric(df["gross_profit"], errors="coerce").fillna(0)
    df["quantity"]     = pd.to_numeric(df["quantity"],     errors="coerce").fillna(0)
    df["cost_total"]   = pd.to_numeric(df["cost_total"],   errors="coerce").fillna(0)
    return df


def get_products_df(business_id: str) -> pd.DataFrame:
    df = read_sheet(SHEET_PRODUCTS)
    if df.empty:
        return pd.DataFrame()
    df = df[df["business_id"] == business_id].copy()
    df["selling_price"]  = pd.to_numeric(df["selling_price"],  errors="coerce").fillna(0)
    df["cost_price"]     = pd.to_numeric(df["cost_price"],     errors="coerce").fillna(0)
    df["stock_quantity"] = pd.to_numeric(df["stock_quantity"], errors="coerce").fillna(0)
    df["reorder_level"]  = pd.to_numeric(df["reorder_level"],  errors="coerce").fillna(0)
    return df


def get_expenses_df(business_id: str) -> pd.DataFrame:
    df = read_sheet(SHEET_EXPENSES)
    if df.empty:
        return pd.DataFrame()
    df = df[df["business_id"] == business_id].copy()
    df["amount"]       = pd.to_numeric(df["amount"],       errors="coerce").fillna(0)
    df["expense_date"] = pd.to_datetime(df["expense_date"], errors="coerce")
    return df


def compute_kpis(sales_df: pd.DataFrame, expenses_df: pd.DataFrame):
    """Return dict of key performance metrics."""
    now   = datetime.now()
    today = now.date()

    kpis = {
        "today_revenue":   0, "week_revenue":    0, "month_revenue":  0,
        "today_profit":    0, "week_profit":     0, "month_profit":   0,
        "today_txn":       0, "week_txn":        0, "month_txn":      0,
        "week_growth":     0, "month_expenses":  0, "net_profit":     0,
    }

    if sales_df.empty:
        return kpis

    df = sales_df.dropna(subset=["sale_date"])

    # Date buckets
    today_df  = df[df["sale_date"].dt.date == today]
    week_df   = df[df["sale_date"] >= (now - timedelta(days=7))]
    month_df  = df[df["sale_date"] >= (now - timedelta(days=30))]
    prev_week = df[
        (df["sale_date"] >= (now - timedelta(days=14))) &
        (df["sale_date"] <  (now - timedelta(days=7)))
    ]

    kpis["today_revenue"]  = today_df["total_amount"].sum()
    kpis["week_revenue"]   = week_df["total_amount"].sum()
    kpis["month_revenue"]  = month_df["total_amount"].sum()
    kpis["today_profit"]   = today_df["gross_profit"].sum()
    kpis["week_profit"]    = week_df["gross_profit"].sum()
    kpis["month_profit"]   = month_df["gross_profit"].sum()
    kpis["today_txn"]      = len(today_df)
    kpis["week_txn"]       = len(week_df)
    kpis["month_txn"]      = len(month_df)

    # Week-on-week growth
    prev_rev = prev_week["total_amount"].sum()
    curr_rev = kpis["week_revenue"]
    if prev_rev > 0:
        kpis["week_growth"] = ((curr_rev - prev_rev) / prev_rev) * 100

    # Expenses & net profit
    if not expenses_df.empty:
        m_exp = expenses_df[expenses_df["expense_date"] >= (now - timedelta(days=30))]
        kpis["month_expenses"] = m_exp["amount"].sum()
    kpis["net_profit"] = kpis["month_profit"] - kpis["month_expenses"]

    return kpis


def compute_insights(sales_df, products_df, expenses_df):
    """Return structured insights dict for the Insights page."""
    insights = {
        "top_products_revenue":  pd.DataFrame(),
        "top_products_qty":      pd.DataFrame(),
        "slow_movers":           pd.DataFrame(),
        "daily_trend":           pd.DataFrame(),
        "weekday_performance":   pd.DataFrame(),
        "category_revenue":      pd.DataFrame(),
        "low_stock":             pd.DataFrame(),
        "stockout_projection":   pd.DataFrame(),
        "payment_split":         pd.DataFrame(),
        "avg_daily_revenue":     0,
        "best_day":              "",
        "worst_day":             "",
    }

    if sales_df.empty:
        return insights

    df = sales_df.dropna(subset=["sale_date"]).copy()

    # Top products by revenue
    top_rev = (
        df.groupby("product_name")["total_amount"]
        .sum().reset_index()
        .sort_values("total_amount", ascending=False)
        .head(10)
    )
    insights["top_products_revenue"] = top_rev

    # Top products by quantity
    top_qty = (
        df.groupby("product_name")["quantity"]
        .sum().reset_index()
        .sort_values("quantity", ascending=False)
        .head(10)
    )
    insights["top_products_qty"] = top_qty

    # Daily trend (last 30 days)
    df["date"] = df["sale_date"].dt.date
    daily = (
        df.groupby("date")["total_amount"]
        .sum().reset_index()
        .sort_values("date")
    )
    insights["daily_trend"]        = daily
    insights["avg_daily_revenue"]  = daily["total_amount"].mean() if not daily.empty else 0

    # Weekday performance
    df["weekday"] = df["sale_date"].dt.day_name()
    wd_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    wd = (
        df.groupby("weekday")["total_amount"]
        .sum().reindex(wd_order, fill_value=0)
        .reset_index()
    )
    wd.columns = ["weekday", "revenue"]
    insights["weekday_performance"] = wd
    if not wd.empty:
        insights["best_day"]  = wd.loc[wd["revenue"].idxmax(), "weekday"]
        insights["worst_day"] = wd.loc[wd["revenue"].idxmin(), "weekday"]

    # Category revenue
    if "category" in df.columns:
        cat = (
            df.groupby("category")["total_amount"]
            .sum().reset_index()
            .sort_values("total_amount", ascending=False)
        )
        insights["category_revenue"] = cat

    # Payment split
    if "payment_method" in df.columns:
        pm = df.groupby("payment_method")["total_amount"].sum().reset_index()
        insights["payment_split"] = pm

    # Slow movers (products sold less than average in last 30 days)
    last30 = df[df["sale_date"] >= (datetime.now() - timedelta(days=30))]
    if not last30.empty:
        prod_sales = last30.groupby("product_name")["quantity"].sum().reset_index()
        avg_qty    = prod_sales["quantity"].mean()
        slow       = prod_sales[prod_sales["quantity"] < avg_qty * 0.5].sort_values("quantity")
        insights["slow_movers"] = slow

    # Low stock & stockout projection
    if not products_df.empty:
        low = products_df[
            products_df["stock_quantity"] <= products_df["reorder_level"]
        ][["product_name","stock_quantity","reorder_level","category"]].copy()
        insights["low_stock"] = low

        # Stockout projection: days_left = current_stock / avg_daily_sales
        proj_rows = []
        for _, prod in products_df.iterrows():
            prod_sales_df = df[df["product_name"] == prod["product_name"]]
            if not prod_sales_df.empty:
                days_range  = max((df["sale_date"].max() - df["sale_date"].min()).days, 1)
                avg_per_day = prod_sales_df["quantity"].sum() / days_range
                if avg_per_day > 0:
                    days_left = prod["stock_quantity"] / avg_per_day
                    proj_rows.append({
                        "product_name": prod["product_name"],
                        "stock_quantity": prod["stock_quantity"],
                        "days_until_stockout": round(days_left, 1),
                        "avg_daily_sales": round(avg_per_day, 2),
                    })
        if proj_rows:
            proj_df = pd.DataFrame(proj_rows).sort_values("days_until_stockout")
            insights["stockout_projection"] = proj_df

    return insights


# ─────────────────────────────────────────────
#  UI COMPONENT HELPERS
# ─────────────────────────────────────────────

def kpi_card(label, value, sub="", positive=None):
    sub_class = ""
    if positive is True:
        sub_class = "kpi-positive"
    elif positive is False:
        sub_class = "kpi-negative"
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-sub {sub_class}">{sub}</div>
    </div>
    """, unsafe_allow_html=True)


def section_header(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def page_header(title, subtitle=""):
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def stock_pill(qty, reorder):
    qty     = safe_int(qty)
    reorder = safe_int(reorder)
    if qty <= 0:
        return '<span class="stock-critical">Out of Stock</span>'
    elif qty <= reorder:
        return f'<span class="stock-low">Low — {qty} left</span>'
    else:
        return f'<span class="stock-ok">{qty} in stock</span>'


# ─────────────────────────────────────────────
#  PAGE: LOGIN
# ─────────────────────────────────────────────

def page_login():
    inject_styles()
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">📊 BizPulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-tagline">Business health at a glance</div>', unsafe_allow_html=True)

    with st.form("login_form"):
        email    = st.text_input("Email address", placeholder="you@business.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if submitted:
        if not email or not password:
            st.error("Please fill in all fields.")
        else:
            with st.spinner("Signing in…"):
                ok, user, msg = login_user(email.strip(), password)
            if ok:
                st.session_state.user        = user
                st.session_state.logged_in   = True
                st.session_state.current_page = "dashboard"
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    st.markdown("Don't have an account?")
    if st.button("Create free account →", use_container_width=True):
        st.session_state.current_page = "signup"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE: SIGNUP
# ─────────────────────────────────────────────

def page_signup():
    inject_styles()
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.markdown('<div class="auth-logo">📊 BizPulse</div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-tagline">Start your 14-day free trial</div>', unsafe_allow_html=True)

    with st.form("signup_form"):
        business_name = st.text_input("Business name", placeholder="Mama Put Express")
        full_name     = st.text_input("Your full name", placeholder="Adaeze Okafor")
        email         = st.text_input("Email address", placeholder="you@business.com")
        password      = st.text_input("Password (min 6 chars)", type="password")
        confirm_pw    = st.text_input("Confirm password", type="password")

        st.markdown("#### Choose your plan")
        plan = st.radio(
            "Plan",
            options=["trial", "monthly", "yearly"],
            format_func=lambda x: {
                "trial":   f"🎁 Free Trial — {PAYMENT_DETAILS['trial_days']} days, no payment needed",
                "monthly": f"📅 Monthly — ₦{PAYMENT_DETAILS['monthly_price']:,}/month",
                "yearly":  f"🏆 Yearly — ₦{PAYMENT_DETAILS['yearly_price']:,}/year (save 2 months!)",
            }[x],
            label_visibility="collapsed",
        )

        submitted = st.form_submit_button("Create Account", use_container_width=True, type="primary")

    if submitted:
        if not all([business_name, full_name, email, password, confirm_pw]):
            st.error("Please fill in all fields.")
        elif password != confirm_pw:
            st.error("Passwords do not match.")
        else:
            with st.spinner("Creating your account…"):
                ok, msg = signup_user(business_name.strip(), full_name.strip(),
                                      email.strip(), password, plan)
            if ok:
                st.success(msg)
                if plan == "trial":
                    st.info("Your 14-day trial is active! Sign in to get started.")
                else:
                    st.session_state.current_page = "pending_payment"
                    st.session_state.pending_email = email.strip()
                    st.session_state.pending_plan  = plan
                    st.rerun()
            else:
                st.error(msg)

    st.markdown("---")
    if st.button("Already have an account? Sign in →", use_container_width=True):
        st.session_state.current_page = "login"
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
#  PAGE: PENDING PAYMENT
# ─────────────────────────────────────────────

def page_pending_payment():
    inject_styles()
    user  = st.session_state.get("user", {})
    plan  = user.get("plan_type") or st.session_state.get("pending_plan", "monthly")
    email = user.get("email")    or st.session_state.get("pending_email", "")
    amount = (PAYMENT_DETAILS["yearly_price"]
              if plan == "yearly"
              else PAYMENT_DETAILS["monthly_price"])

    page_header("💳 Complete Your Payment", "One step away from full access")

    col1, col2 = st.columns([3, 2])
    with col1:
        st.info(f"""
**Transfer ₦{amount:,} to:**

🏦 **Bank:** {PAYMENT_DETAILS['bank']}
👤 **Account Name:** {PAYMENT_DETAILS['account_name']}
🔢 **Account Number:** `{PAYMENT_DETAILS['account_number']}`

📌 **Use your email as payment reference:**
`{email}`

After transfer, your account will be activated within **24 hours**.
        """)

        st.markdown("---")
        st.markdown("**Already paid?** We'll activate your account shortly. "
                    "You'll be able to log in once activated.")

    with col2:
        st.markdown("#### Plan Summary")
        kpi_card("Plan Type", plan.capitalize(), f"₦{amount:,}", True)
        kpi_card("Email", email, "Use as transfer reference")

    if st.button("← Back to Login"):
        st.session_state.current_page = "login"
        st.rerun()


# ─────────────────────────────────────────────
#  PAGE: DASHBOARD
# ─────────────────────────────────────────────

def page_dashboard():
    user        = st.session_state.user
    business_id = user["business_id"]

    page_header(
        f"👋 {user.get('business_name', 'Dashboard')}",
        f"Here's your business snapshot — {datetime.now().strftime('%A, %d %B %Y')}"
    )

    with st.spinner("Loading your data…"):
        sales_df    = get_sales_df(business_id)
        products_df = get_products_df(business_id)
        expenses_df = get_expenses_df(business_id)
        kpis        = compute_kpis(sales_df, expenses_df)

    # ── KPI Row 1 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Today's Revenue", fmt_naira(kpis["today_revenue"]),
                 f"{kpis['today_txn']} transactions today")
    with c2:
        growth = kpis["week_growth"]
        kpi_card("This Week", fmt_naira(kpis["week_revenue"]),
                 f"{'▲' if growth >= 0 else '▼'} {abs(growth):.1f}% vs last week",
                 positive=(growth >= 0))
    with c3:
        kpi_card("This Month", fmt_naira(kpis["month_revenue"]),
                 f"{kpis['month_txn']} transactions")
    with c4:
        kpi_card("Net Profit (Month)", fmt_naira(kpis["net_profit"]),
                 f"After ₦{kpis['month_expenses']:,.0f} expenses",
                 positive=(kpis["net_profit"] >= 0))

    # ── KPI Row 2 ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Today's Profit", fmt_naira(kpis["today_profit"]), "Gross margin today")
    with c2:
        kpi_card("Week Profit", fmt_naira(kpis["week_profit"]), "Gross margin this week")
    with c3:
        total_products = len(products_df) if not products_df.empty else 0
        kpi_card("Products", str(total_products), "Active in inventory")
    with c4:
        if not products_df.empty:
            low_count = len(products_df[
                products_df["stock_quantity"] <= products_df["reorder_level"]
            ])
        else:
            low_count = 0
        kpi_card("Low Stock Alerts", str(low_count),
                 "Products need restocking",
                 positive=(low_count == 0))

    # ── Charts ──
    if not sales_df.empty:
        col_left, col_right = st.columns([3, 2])

        with col_left:
            section_header("Revenue Trend — Last 30 Days")
            trend_df = sales_df.copy()
            trend_df["date"] = trend_df["sale_date"].dt.date
            trend_df = (
                trend_df[trend_df["sale_date"] >= (datetime.now() - timedelta(days=30))]
                .groupby("date")["total_amount"].sum()
                .reset_index()
            )
            if not trend_df.empty:
                fig = px.area(
                    trend_df, x="date", y="total_amount",
                    labels={"total_amount": "Revenue (₦)", "date": ""},
                    color_discrete_sequence=["#6366f1"],
                )
                fig.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    yaxis=dict(tickprefix="₦", gridcolor="#f1f5f9"),
                    xaxis=dict(gridcolor="#f1f5f9"),
                    height=280,
                )
                fig.update_traces(fill="tozeroy", line_color="#6366f1",
                                  fillcolor="rgba(99,102,241,0.15)")
                st.plotly_chart(fig, use_container_width=True)

        with col_right:
            section_header("Sales by Payment Method")
            pm_df = (
                sales_df.groupby("payment_method")["total_amount"]
                .sum().reset_index()
            )
            if not pm_df.empty:
                fig2 = px.pie(
                    pm_df, values="total_amount", names="payment_method",
                    color_discrete_sequence=["#6366f1","#10b981","#f59e0b","#ef4444"],
                    hole=0.55,
                )
                fig2.update_layout(
                    margin=dict(l=0, r=0, t=10, b=0),
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=280,
                    legend=dict(orientation="h", y=-0.1),
                )
                st.plotly_chart(fig2, use_container_width=True)

        # Top products
        section_header("Top Selling Products (by Revenue)")
        top_df = (
            sales_df.groupby("product_name")["total_amount"]
            .sum().reset_index()
            .sort_values("total_amount", ascending=True)
            .tail(8)
        )
        if not top_df.empty:
            fig3 = px.bar(
                top_df, x="total_amount", y="product_name",
                orientation="h",
                labels={"total_amount": "Revenue (₦)", "product_name": ""},
                color_discrete_sequence=["#6366f1"],
            )
            fig3.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickprefix="₦", gridcolor="#f1f5f9"),
                height=300,
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("📭 No sales data yet. Record your first sale to see analytics here.")

    # ── Low Stock Alerts ──
    if not products_df.empty:
        low_stock = products_df[
            products_df["stock_quantity"] <= products_df["reorder_level"]
        ]
        if not low_stock.empty:
            section_header("⚠️ Low Stock Alerts")
            for _, row in low_stock.iterrows():
                qty = safe_int(row["stock_quantity"])
                lvl = safe_int(row["reorder_level"])
                css = "alert-critical" if qty <= 0 else "alert-low"
                st.markdown(
                    f'<div class="{css}">🔔 <strong>{row["product_name"]}</strong> — '
                    f'{qty} units left (reorder level: {lvl})</div>',
                    unsafe_allow_html=True,
                )


# ─────────────────────────────────────────────
#  PAGE: RECORD SALE
# ─────────────────────────────────────────────

def page_record_sale():
    user        = st.session_state.user
    business_id = user["business_id"]

    page_header("🛒 Record a Sale", "Log a transaction and update inventory automatically")

    products_df = get_products_df(business_id)

    if products_df.empty:
        st.warning("You have no products yet. Add products first before recording sales.")
        if st.button("→ Go to Product Management"):
            st.session_state.current_page = "products"
            st.rerun()
        return

    # Only show in-stock products
    available = products_df[products_df["stock_quantity"] > 0].copy()
    if available.empty:
        st.error("All products are out of stock. Please restock before recording sales.")
        return

    col1, col2 = st.columns([2, 1])

    with col1:
        with st.form("record_sale_form", clear_on_submit=True):
            # Product selector
            product_options = {
                f"{r['product_name']} (Stock: {int(r['stock_quantity'])} | ₦{r['selling_price']:,.0f})": r
                for _, r in available.iterrows()
            }
            selected_label = st.selectbox("Select product", list(product_options.keys()))
            selected_product = product_options[selected_label]

            max_qty = int(selected_product["stock_quantity"])
            quantity = st.number_input(
                "Quantity", min_value=1, max_value=max_qty,
                value=1, step=1,
                help=f"Max available: {max_qty} units"
            )

            payment_method = st.selectbox(
                "Payment method", ["Cash", "Bank Transfer", "POS", "Mobile Money"]
            )

            # Live calculation display
            unit_price   = safe_float(selected_product["selling_price"])
            cost_price   = safe_float(selected_product["cost_price"])
            total        = unit_price * quantity
            cost_total   = cost_price * quantity
            gross_profit = total - cost_total

            st.markdown(f"""
            <div class="kpi-card" style="margin-top:1rem;">
                <div class="kpi-label">Sale Summary</div>
                <div style="display:flex; gap:2rem; margin-top:0.5rem;">
                    <div>
                        <div class="kpi-label">Unit Price</div>
                        <div style="font-weight:700;font-size:1.1rem;color:#f1f5f9">{fmt_naira(unit_price)}</div>
                    </div>
                    <div>
                        <div class="kpi-label">Quantity</div>
                        <div style="font-weight:700;font-size:1.1rem;color:#f1f5f9">{quantity}</div>
                    </div>
                    <div>
                        <div class="kpi-label">Total Amount</div>
                        <div style="font-weight:800;font-size:1.4rem;color:#34d399">{fmt_naira(total)}</div>
                    </div>
                    <div>
                        <div class="kpi-label">Gross Profit</div>
                        <div style="font-weight:700;font-size:1.1rem;color:#a5b4fc">{fmt_naira(gross_profit)}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            submitted = st.form_submit_button(
                f"✅ Record Sale — {fmt_naira(total)}", use_container_width=True, type="primary"
            )

        if submitted:
            sale_id  = gen_id("SAL")
            now_str  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Write sale row
            sale_row = [
                sale_id, business_id,
                selected_product["product_id"],
                selected_product["product_name"],
                quantity, unit_price, total,
                cost_total, gross_profit,
                payment_method, now_str,
                user.get("full_name", user.get("email", ""))
            ]
            sale_ok = append_row(SHEET_SALES, sale_row)

            if sale_ok:
                # Deduct stock
                new_stock = int(selected_product["stock_quantity"]) - quantity
                stock_ok  = update_row_by_id(
                    SHEET_PRODUCTS, "product_id",
                    selected_product["product_id"],
                    {"stock_quantity": new_stock}
                )
                if stock_ok:
                    st.success(
                        f"✅ Sale recorded! {fmt_naira(total)} | "
                        f"Stock remaining: {new_stock} units"
                    )
                    if new_stock <= safe_int(selected_product["reorder_level"]):
                        st.warning(
                            f"⚠️ Low stock alert: {selected_product['product_name']} "
                            f"is at or below reorder level ({safe_int(selected_product['reorder_level'])} units)."
                        )
                else:
                    st.warning("Sale recorded but stock update failed. Please update manually.")
            else:
                st.error("Failed to record sale. Please try again.")

    with col2:
        section_header("Today's Sales")
        sales_df = get_sales_df(business_id)
        if not sales_df.empty:
            today = datetime.now().date()
            today_sales = sales_df[sales_df["sale_date"].dt.date == today]
            kpi_card("Today's Revenue",
                     fmt_naira(today_sales["total_amount"].sum()),
                     f"{len(today_sales)} transactions")
            kpi_card("Today's Profit",
                     fmt_naira(today_sales["gross_profit"].sum()),
                     "Gross margin")

            if not today_sales.empty:
                st.markdown("**Recent transactions:**")
                recent = today_sales.sort_values("sale_date", ascending=False).head(5)
                for _, r in recent.iterrows():
                    st.markdown(
                        f"• **{r['product_name']}** × {int(r['quantity'])} "
                        f"= {fmt_naira(r['total_amount'])} _{r['payment_method']}_"
                    )
        else:
            kpi_card("Today's Revenue", "₦0.00", "No sales yet today")


# ─────────────────────────────────────────────
#  PAGE: PRODUCT MANAGEMENT
# ─────────────────────────────────────────────

def page_products():
    user        = st.session_state.user
    business_id = user["business_id"]

    page_header("📦 Product Management", "Add, edit and manage your inventory")

    tab1, tab2, tab3 = st.tabs(["📋 All Products", "➕ Add Product", "🔄 Restock"])

    # ── Tab 1: View All ──
    with tab1:
        products_df = get_products_df(business_id)
        if products_df.empty:
            st.info("No products yet. Add your first product in the 'Add Product' tab.")
        else:
            # Summary metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                kpi_card("Total Products", str(len(products_df)), "In your catalog")
            with c2:
                total_stock_val = (products_df["stock_quantity"] * products_df["selling_price"]).sum()
                kpi_card("Inventory Value", fmt_naira(total_stock_val), "At selling price")
            with c3:
                total_cost_val = (products_df["stock_quantity"] * products_df["cost_price"]).sum()
                kpi_card("Inventory Cost", fmt_naira(total_cost_val), "At cost price")
            with c4:
                low_count = len(products_df[products_df["stock_quantity"] <= products_df["reorder_level"]])
                kpi_card("Low Stock", str(low_count), "Need restocking", positive=(low_count == 0))

            st.markdown("---")

            # Category filter
            cats = ["All"] + sorted(products_df["category"].unique().tolist())
            selected_cat = st.selectbox("Filter by category", cats)
            disp = products_df if selected_cat == "All" else products_df[products_df["category"] == selected_cat]

            # Display product cards
            for _, row in disp.iterrows():
                with st.expander(
                    f"**{row['product_name']}** | {row['category']} | "
                    f"Stock: {int(row['stock_quantity'])} | {fmt_naira(row['selling_price'])}",
                    expanded=False
                ):
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        st.markdown(f"**Cost Price:** {fmt_naira(row['cost_price'])}")
                        st.markdown(f"**Selling Price:** {fmt_naira(row['selling_price'])}")
                        margin = safe_float(row['selling_price']) - safe_float(row['cost_price'])
                        st.markdown(f"**Margin/unit:** {fmt_naira(margin)}")
                    with ec2:
                        st.markdown(f"**Stock:** {int(row['stock_quantity'])} units")
                        st.markdown(f"**Reorder Level:** {int(row['reorder_level'])} units")
                        st.markdown(f"**Category:** {row['category']}")
                    with ec3:
                        st.markdown(
                            stock_pill(row["stock_quantity"], row["reorder_level"]),
                            unsafe_allow_html=True
                        )

                    # Edit form
                    with st.form(f"edit_{row['product_id']}"):
                        st.markdown("**Edit Product**")
                        f1, f2 = st.columns(2)
                        new_name     = f1.text_input("Product Name", value=row["product_name"])
                        new_cat      = f2.text_input("Category",     value=row["category"])
                        new_cost     = f1.number_input("Cost Price",    value=safe_float(row["cost_price"]),    min_value=0.0, step=50.0)
                        new_sell     = f2.number_input("Selling Price", value=safe_float(row["selling_price"]), min_value=0.0, step=50.0)
                        new_reorder  = f1.number_input("Reorder Level", value=safe_int(row["reorder_level"]),   min_value=0,   step=1)
                        save = st.form_submit_button("💾 Save Changes", type="primary")

                    if save:
                        ok = update_row_by_id(
                            SHEET_PRODUCTS, "product_id", row["product_id"],
                            {
                                "product_name": new_name, "category": new_cat,
                                "cost_price": new_cost, "selling_price": new_sell,
                                "reorder_level": new_reorder,
                            }
                        )
                        st.success("Product updated!") if ok else st.error("Update failed.")
                        st.rerun()

                    if st.button(f"🗑️ Delete {row['product_name']}", key=f"del_{row['product_id']}"):
                        ok = delete_row_by_id(SHEET_PRODUCTS, "product_id", row["product_id"])
                        st.success("Product deleted.") if ok else st.error("Delete failed.")
                        st.rerun()

    # ── Tab 2: Add Product ──
    with tab2:
        with st.form("add_product_form", clear_on_submit=True):
            st.markdown("#### New Product Details")
            f1, f2 = st.columns(2)
            prod_name   = f1.text_input("Product Name *",     placeholder="e.g. Indomie Chicken 70g")
            category    = f2.text_input("Category *",         placeholder="e.g. Noodles, Beverages")
            cost_price  = f1.number_input("Cost Price (₦) *",    min_value=0.0, step=50.0,
                                          help="What you paid per unit")
            sell_price  = f2.number_input("Selling Price (₦) *", min_value=0.0, step=50.0,
                                          help="What the customer pays")
            stock_qty   = f1.number_input("Opening Stock *",  min_value=0, step=1,
                                          help="How many units you have right now")
            reorder_lvl = f2.number_input("Reorder Level *",  min_value=0, step=1,
                                          help="Alert me when stock falls to this level")

            if cost_price > 0 and sell_price > 0:
                margin  = sell_price - cost_price
                margin_pct = (margin / sell_price) * 100
                st.info(f"💡 Profit margin: **{fmt_naira(margin)}** per unit ({margin_pct:.1f}%)")

            submitted = st.form_submit_button("➕ Add Product", use_container_width=True, type="primary")

        if submitted:
            if not all([prod_name, category]) or sell_price <= 0:
                st.error("Please fill in all required fields and ensure selling price > 0.")
            else:
                product_id = gen_id("PRD")
                now_str    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                row = [
                    product_id, business_id, prod_name.strip(),
                    category.strip(), cost_price, sell_price,
                    stock_qty, reorder_lvl, now_str
                ]
                ok = append_row(SHEET_PRODUCTS, row)
                if ok:
                    st.success(f"✅ '{prod_name}' added to your inventory!")
                    st.rerun()
                else:
                    st.error("Failed to add product. Please try again.")

    # ── Tab 3: Restock ──
    with tab3:
        products_df = get_products_df(business_id)
        if products_df.empty:
            st.info("No products found. Add products first.")
        else:
            st.markdown("#### Add Stock to Existing Product")
            with st.form("restock_form", clear_on_submit=True):
                product_options = {
                    f"{r['product_name']} (Current: {int(r['stock_quantity'])} units)": r
                    for _, r in products_df.iterrows()
                }
                selected_label   = st.selectbox("Select product", list(product_options.keys()))
                selected_product = product_options[selected_label]

                add_qty = st.number_input("Units to add", min_value=1, step=1, value=10)
                restock_note = st.text_input("Note (optional)", placeholder="e.g. Weekly supplier delivery")
                submitted = st.form_submit_button("🔄 Update Stock", use_container_width=True, type="primary")

            if submitted:
                new_qty = int(selected_product["stock_quantity"]) + add_qty
                ok = update_row_by_id(
                    SHEET_PRODUCTS, "product_id",
                    selected_product["product_id"],
                    {"stock_quantity": new_qty}
                )
                if ok:
                    st.success(
                        f"✅ Stock updated! {selected_product['product_name']}: "
                        f"{int(selected_product['stock_quantity'])} → {new_qty} units"
                    )
                    st.rerun()
                else:
                    st.error("Failed to update stock.")


# ─────────────────────────────────────────────
#  PAGE: EXPENSES
# ─────────────────────────────────────────────

def page_expenses():
    user        = st.session_state.user
    business_id = user["business_id"]

    page_header("💸 Expense Tracker", "Log and monitor your business expenses")

    tab1, tab2 = st.tabs(["📋 View Expenses", "➕ Log Expense"])

    with tab1:
        expenses_df = get_expenses_df(business_id)
        if expenses_df.empty:
            st.info("No expenses logged yet.")
        else:
            # Date filter
            col1, col2 = st.columns(2)
            start_date = col1.date_input("From", value=(datetime.now() - timedelta(days=30)).date())
            end_date   = col2.date_input("To",   value=datetime.now().date())

            filtered = expenses_df[
                (expenses_df["expense_date"].dt.date >= start_date) &
                (expenses_df["expense_date"].dt.date <= end_date)
            ]

            c1, c2, c3 = st.columns(3)
            with c1:
                kpi_card("Total Expenses", fmt_naira(filtered["amount"].sum()),
                         f"In selected period")
            with c2:
                kpi_card("Transactions", str(len(filtered)), "Expense entries")
            with c3:
                avg = filtered["amount"].mean() if not filtered.empty else 0
                kpi_card("Average Expense", fmt_naira(avg), "Per entry")

            if not filtered.empty:
                # Category breakdown
                cat_breakdown = (
                    filtered.groupby("category")["amount"]
                    .sum().reset_index()
                    .sort_values("amount", ascending=False)
                )
                if not cat_breakdown.empty:
                    fig = px.bar(
                        cat_breakdown, x="category", y="amount",
                        labels={"amount": "Amount (₦)", "category": "Category"},
                        color_discrete_sequence=["#ef4444"],
                        title="Expenses by Category"
                    )
                    fig.update_layout(
                        plot_bgcolor="rgba(0,0,0,0)",
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(l=0, r=0, t=40, b=0),
                        height=280,
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # Table
                st.dataframe(
                    filtered[["expense_date","expense_name","category","amount","recorded_by"]]
                    .sort_values("expense_date", ascending=False)
                    .rename(columns={
                        "expense_date":  "Date",
                        "expense_name":  "Description",
                        "category":      "Category",
                        "amount":        "Amount (₦)",
                        "recorded_by":   "Recorded By",
                    }),
                    use_container_width=True,
                )

    with tab2:
        with st.form("log_expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            exp_name = col1.text_input("Description *", placeholder="e.g. Generator fuel")
            category = col2.selectbox("Category", [
                "Rent", "Utilities", "Salaries", "Supplies", "Transport",
                "Marketing", "Maintenance", "Taxes", "Miscellaneous"
            ])
            amount      = col1.number_input("Amount (₦) *", min_value=0.0, step=100.0)
            expense_date = col2.date_input("Date", value=datetime.now().date())
            submitted = st.form_submit_button("Log Expense", use_container_width=True, type="primary")

        if submitted:
            if not exp_name or amount <= 0:
                st.error("Please fill in description and a valid amount.")
            else:
                expense_id = gen_id("EXP")
                row = [
                    expense_id, business_id,
                    exp_name.strip(), category,
                    amount, str(expense_date),
                    user.get("full_name", user.get("email", ""))
                ]
                ok = append_row(SHEET_EXPENSES, row)
                if ok:
                    st.success(f"✅ Expense logged: {exp_name} — {fmt_naira(amount)}")
                    st.rerun()
                else:
                    st.error("Failed to log expense.")


# ─────────────────────────────────────────────
#  PAGE: BUSINESS INSIGHTS
# ─────────────────────────────────────────────

def page_insights():
    user        = st.session_state.user
    business_id = user["business_id"]

    page_header("🧠 Business Insights", "Data-driven intelligence for smarter decisions")

    with st.spinner("Crunching your numbers…"):
        sales_df    = get_sales_df(business_id)
        products_df = get_products_df(business_id)
        expenses_df = get_expenses_df(business_id)
        insights    = compute_insights(sales_df, products_df, expenses_df)

    if sales_df.empty:
        st.info("📭 No data yet. Record some sales to unlock insights.")
        return

    # ── Summary Stats ──
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Avg Daily Revenue",
                 fmt_naira(insights["avg_daily_revenue"]), "Based on all recorded days")
    with c2:
        kpi_card("Best Sales Day", insights.get("best_day", "N/A"), "Highest revenue weekday")
    with c3:
        kpi_card("Slowest Day", insights.get("worst_day", "N/A"), "Lowest revenue weekday")
    with c4:
        if not insights["top_products_revenue"].empty:
            best = insights["top_products_revenue"].iloc[0]["product_name"]
        else:
            best = "N/A"
        kpi_card("Best Seller", best, "By total revenue")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Trends", "🏆 Products", "📦 Inventory", "📅 Weekday", "📊 Export"
    ])

    # ── Tab 1: Trends ──
    with tab1:
        section_header("Daily Revenue Trend")
        if not insights["daily_trend"].empty:
            fig = px.line(
                insights["daily_trend"], x="date", y="total_amount",
                labels={"total_amount": "Revenue (₦)", "date": ""},
                color_discrete_sequence=["#6366f1"],
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(tickprefix="₦", gridcolor="#f1f5f9"),
                height=320,
            )
            fig.update_traces(line_width=2.5, mode="lines+markers")
            st.plotly_chart(fig, use_container_width=True)

        section_header("Category Performance")
        if not insights["category_revenue"].empty:
            fig2 = px.bar(
                insights["category_revenue"], x="category", y="total_amount",
                labels={"total_amount": "Revenue (₦)", "category": ""},
                color_discrete_sequence=["#10b981"],
            )
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0), height=280,
            )
            st.plotly_chart(fig2, use_container_width=True)

    # ── Tab 2: Products ──
    with tab2:
        col_l, col_r = st.columns(2)
        with col_l:
            section_header("Top Products by Revenue")
            if not insights["top_products_revenue"].empty:
                fig = px.bar(
                    insights["top_products_revenue"].sort_values("total_amount"),
                    x="total_amount", y="product_name", orientation="h",
                    labels={"total_amount": "Revenue (₦)", "product_name": ""},
                    color_discrete_sequence=["#6366f1"],
                )
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=10, b=0), height=350,
                    xaxis=dict(tickprefix="₦"),
                )
                st.plotly_chart(fig, use_container_width=True)

        with col_r:
            section_header("Top Products by Quantity Sold")
            if not insights["top_products_qty"].empty:
                fig2 = px.bar(
                    insights["top_products_qty"].sort_values("quantity"),
                    x="quantity", y="product_name", orientation="h",
                    labels={"quantity": "Units Sold", "product_name": ""},
                    color_discrete_sequence=["#10b981"],
                )
                fig2.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=0, r=0, t=10, b=0), height=350,
                )
                st.plotly_chart(fig2, use_container_width=True)

        section_header("⚠️ Slow-Moving Products (Last 30 Days)")
        if not insights["slow_movers"].empty:
            st.dataframe(
                insights["slow_movers"].rename(
                    columns={"product_name":"Product","quantity":"Units Sold (30d)"}
                ),
                use_container_width=True,
            )
        else:
            st.markdown('<div class="alert-success">✅ All products are selling at healthy rates.</div>',
                        unsafe_allow_html=True)

    # ── Tab 3: Inventory ──
    with tab3:
        section_header("🔴 Low Stock Products")
        if not insights["low_stock"].empty:
            for _, r in insights["low_stock"].iterrows():
                qty = safe_int(r["stock_quantity"])
                css = "alert-critical" if qty <= 0 else "alert-low"
                st.markdown(
                    f'<div class="{css}">⚠️ <strong>{r["product_name"]}</strong> '
                    f'— {qty} units left (reorder at {safe_int(r["reorder_level"])})</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="alert-success">✅ All products have sufficient stock.</div>',
                        unsafe_allow_html=True)

        section_header("📅 Projected Stockout Dates")
        if not insights["stockout_projection"].empty:
            proj = insights["stockout_projection"].copy()
            proj["stockout_date"] = proj["days_until_stockout"].apply(
                lambda d: (datetime.now() + timedelta(days=d)).strftime("%d %b %Y")
            )
            proj["urgency"] = proj["days_until_stockout"].apply(
                lambda d: "🔴 Critical" if d <= 3 else ("🟡 Soon" if d <= 7 else "🟢 OK")
            )
            st.dataframe(
                proj[["product_name","stock_quantity","avg_daily_sales",
                       "days_until_stockout","stockout_date","urgency"]]
                .rename(columns={
                    "product_name":       "Product",
                    "stock_quantity":     "Current Stock",
                    "avg_daily_sales":    "Avg Daily Sales",
                    "days_until_stockout":"Days Left",
                    "stockout_date":      "Est. Stockout Date",
                    "urgency":            "Status",
                }),
                use_container_width=True,
            )
        else:
            st.info("Not enough sales history to project stockout dates.")

    # ── Tab 4: Weekday ──
    with tab4:
        section_header("Revenue by Day of Week")
        if not insights["weekday_performance"].empty:
            wd = insights["weekday_performance"]
            colors = ["#ef4444" if r == wd["revenue"].min()
                      else ("#10b981" if r == wd["revenue"].max() else "#6366f1")
                      for r in wd["revenue"]]
            fig = go.Figure(go.Bar(
                x=wd["weekday"], y=wd["revenue"],
                marker_color=colors,
                text=[fmt_naira(v) for v in wd["revenue"]],
                textposition="outside",
            ))
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                yaxis=dict(tickprefix="₦", gridcolor="#f1f5f9"),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

            if insights["best_day"] and insights["worst_day"]:
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(
                        f'<div class="alert-success">🏆 <strong>Best day:</strong> '
                        f'{insights["best_day"]} — schedule more staff and stock up.</div>',
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(
                        f'<div class="alert-low">💡 <strong>Slowest day:</strong> '
                        f'{insights["worst_day"]} — consider promotions or discounts.</div>',
                        unsafe_allow_html=True
                    )

    # ── Tab 5: Export ──
    with tab5:
        section_header("📥 Download Your Data")
        col1, col2, col3 = st.columns(3)

        with col1:
            if not sales_df.empty:
                csv = sales_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Sales CSV",
                    data=csv, file_name="sales_export.csv",
                    mime="text/csv", use_container_width=True,
                )

        with col2:
            if not products_df.empty:
                csv = products_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Products CSV",
                    data=csv, file_name="products_export.csv",
                    mime="text/csv", use_container_width=True,
                )

        with col3:
            if not expenses_df.empty:
                csv = expenses_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "⬇️ Download Expenses CSV",
                    data=csv, file_name="expenses_export.csv",
                    mime="text/csv", use_container_width=True,
                )


# ─────────────────────────────────────────────
#  PAGE: ADMIN PANEL
# ─────────────────────────────────────────────

def page_admin():
    page_header("🛡️ Admin Panel", "BizPulse platform management")

    users_df = read_sheet(SHEET_USERS)

    if users_df.empty:
        st.info("No users found.")
        return

    # Platform stats
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Total Businesses", str(len(users_df)), "Registered accounts")
    with c2:
        active = len(users_df[users_df["plan_status"] == "active"])
        kpi_card("Active Subscriptions", str(active), "Paying or trial users")
    with c3:
        pending = len(users_df[users_df["plan_status"] == "pending_payment"])
        kpi_card("Pending Payment", str(pending), "Awaiting manual activation")
    with c4:
        monthly_rev = len(users_df[
            (users_df["plan_type"] == "monthly") &
            (users_df["plan_status"] == "active")
        ]) * PAYMENT_DETAILS["monthly_price"]
        yearly_rev = len(users_df[
            (users_df["plan_type"] == "yearly") &
            (users_df["plan_status"] == "active")
        ]) * (PAYMENT_DETAILS["yearly_price"] / 12)
        kpi_card("Est. Monthly Revenue",
                 fmt_naira(monthly_rev + yearly_rev), "From active paid plans")

    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["⏳ Pending Activation", "✅ Active Users", "👥 All Users"])

    # ── Pending ──
    with tab1:
        pending_df = users_df[users_df["plan_status"] == "pending_payment"]
        if pending_df.empty:
            st.success("No pending activations.")
        else:
            for _, u in pending_df.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 2])
                    with col1:
                        st.markdown(f"**{u['business_name']}** — {u['full_name']}")
                        st.caption(f"📧 {u['email']} | Plan: {u['plan_type']} | Signed up: {u['created_at']}")
                    with col2:
                        plan   = u["plan_type"]
                        days   = 30 if plan == "monthly" else 365
                        end_dt = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
                        if st.button(f"✅ Activate", key=f"act_{u['user_id']}"):
                            ok = update_row_by_id(
                                SHEET_USERS, "user_id", u["user_id"],
                                {
                                    "plan_status":       "active",
                                    "subscription_start": datetime.now().strftime("%Y-%m-%d"),
                                    "subscription_end":   end_dt,
                                }
                            )
                            if ok:
                                st.success(f"✅ {u['business_name']} activated until {end_dt}")
                                st.rerun()
                    with col3:
                        if st.button("🗑️ Delete", key=f"del_u_{u['user_id']}"):
                            delete_row_by_id(SHEET_USERS, "user_id", u["user_id"])
                            st.rerun()
                    st.markdown("---")

    # ── Active ──
    with tab2:
        active_df = users_df[users_df["plan_status"] == "active"]
        if active_df.empty:
            st.info("No active users.")
        else:
            for _, u in active_df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 2])
                with col1:
                    st.markdown(f"**{u['business_name']}** — {u['full_name']}")
                    st.caption(f"📧 {u['email']} | {u['plan_type']} | Expires: {u.get('subscription_end','?')}")
                with col2:
                    # Extend by 30 days
                    if st.button("🔁 Extend 30d", key=f"ext_{u['user_id']}"):
                        curr_end = parse_date(u.get("subscription_end", ""))
                        base     = curr_end if (curr_end and curr_end > datetime.now()) else datetime.now()
                        new_end  = (base + timedelta(days=30)).strftime("%Y-%m-%d")
                        update_row_by_id(SHEET_USERS, "user_id", u["user_id"],
                                         {"subscription_end": new_end})
                        st.success(f"Extended to {new_end}")
                        st.rerun()
                with col3:
                    if st.button("⛔ Deactivate", key=f"deact_{u['user_id']}"):
                        update_row_by_id(SHEET_USERS, "user_id", u["user_id"],
                                         {"plan_status": "expired"})
                        st.rerun()
                st.markdown("---")

    # ── All Users ──
    with tab3:
        show_cols = ["business_name","full_name","email","plan_type","plan_status","subscription_end","created_at"]
        display   = users_df[[c for c in show_cols if c in users_df.columns]]
        st.dataframe(display, use_container_width=True)
        csv = display.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Export All Users CSV", data=csv,
                           file_name="bizpulse_users.csv", mime="text/csv")


# ─────────────────────────────────────────────
#  SIDEBAR NAVIGATION
# ─────────────────────────────────────────────

def render_sidebar():
    user = st.session_state.get("user", {})
    is_admin = user.get("role") == "admin"

    with st.sidebar:
        st.markdown("""
        <div style="padding:1rem 0 1.5rem 0; text-align:center;">
            <div style="font-size:1.6rem;font-weight:800;color:#f1f5f9;">📊 BizPulse</div>
            <div style="font-size:0.7rem;color:#475569;margin-top:0.2rem;letter-spacing:0.1em;
                        text-transform:uppercase;">Business Intelligence</div>
        </div>
        """, unsafe_allow_html=True)

        # Business info
        st.markdown(f"""
        <div style="background:#1e293b;border-radius:10px;padding:0.75rem 1rem;margin-bottom:1.5rem;">
            <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                        letter-spacing:0.08em;font-weight:600;">Logged in as</div>
            <div style="font-size:0.9rem;font-weight:700;color:#f1f5f9;margin-top:0.2rem;">
                {user.get('full_name','User')}</div>
            <div style="font-size:0.75rem;color:#64748b;">{user.get('business_name','')}</div>
        </div>
        """, unsafe_allow_html=True)

        # Nav items
        nav_items = [
            ("dashboard",  "🏠", "Dashboard"),
            ("record_sale","🛒", "Record Sale"),
            ("products",   "📦", "Products"),
            ("expenses",   "💸", "Expenses"),
            ("insights",   "🧠", "Insights"),
        ]
        if is_admin:
            nav_items.append(("admin", "🛡️", "Admin Panel"))

        current = st.session_state.get("current_page", "dashboard")
        for page_key, icon, label in nav_items:
            is_active = current == page_key
            if st.button(
                f"{icon}  {label}",
                key=f"nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_page = page_key
                st.rerun()

        st.markdown("---")

        # Subscription badge
        plan_status = user.get("plan_status", "")
        plan_type   = user.get("plan_type", "")
        sub_end     = user.get("subscription_end", "")

        if plan_status == "active":
            end_dt = parse_date(sub_end)
            days_left = (end_dt - datetime.now()).days if end_dt else 0
            color = "#10b981" if days_left > 7 else "#f59e0b"
            st.markdown(f"""
            <div style="background:#1e293b;border-radius:10px;padding:0.75rem 1rem;margin-bottom:1rem;">
                <div style="font-size:0.65rem;color:#475569;text-transform:uppercase;
                            letter-spacing:0.08em;">Subscription</div>
                <div style="font-size:0.85rem;font-weight:700;color:{color};margin-top:0.2rem;">
                    ✅ {plan_type.capitalize()} — Active</div>
                <div style="font-size:0.7rem;color:#64748b;">{days_left} days remaining</div>
            </div>
            """, unsafe_allow_html=True)

        if st.button("🚪  Sign Out", use_container_width=True):
            for key in ["user","logged_in","current_page"]:
                st.session_state.pop(key, None)
            st.rerun()


# ─────────────────────────────────────────────
#  SUBSCRIPTION GUARD
# ─────────────────────────────────────────────

def check_access():
    """
    Returns True if user can access the app.
    Handles pending payment and expired subscriptions.
    """
    user = st.session_state.get("user", {})
    role = user.get("role", "")

    # Admin always has access
    if role == "admin":
        return True

    status = user.get("plan_status", "")

    if status == "pending_payment":
        page_pending_payment()
        return False

    if status == "expired":
        inject_styles()
        page_header("⏰ Subscription Expired", "Your access period has ended.")
        st.warning(
            "Your subscription has expired. Please make a payment to continue "
            "accessing BizPulse."
        )
        st.info(f"""
**Renew your subscription:**

🏦 Bank: {PAYMENT_DETAILS['bank']}
👤 Account Name: {PAYMENT_DETAILS['account_name']}
🔢 Account Number: `{PAYMENT_DETAILS['account_number']}`

📌 Use your email **{user.get('email','')}** as reference.
Monthly: ₦{PAYMENT_DETAILS['monthly_price']:,} | Yearly: ₦{PAYMENT_DETAILS['yearly_price']:,}

Your account will be reactivated within 24 hours of payment.
        """)
        if st.button("Sign Out"):
            for key in ["user","logged_in","current_page"]:
                st.session_state.pop(key, None)
            st.rerun()
        return False

    if not is_subscription_active(user):
        # Auto-mark as expired
        update_row_by_id(SHEET_USERS, "user_id", user["user_id"], {"plan_status": "expired"})
        st.session_state.user["plan_status"] = "expired"
        st.rerun()

    return True


# ─────────────────────────────────────────────
#  MAIN ROUTER
# ─────────────────────────────────────────────

def main():
    inject_styles()

    # Initialise session state keys
    if "logged_in"    not in st.session_state: st.session_state.logged_in    = False
    if "current_page" not in st.session_state: st.session_state.current_page = "login"
    if "user"         not in st.session_state: st.session_state.user         = {}

    # ── Not logged in ──
    if not st.session_state.logged_in:
        if st.session_state.current_page == "signup":
            page_signup()
        elif st.session_state.current_page == "pending_payment":
            page_pending_payment()
        else:
            page_login()
        return

    # ── Logged in: check access ──
    if not check_access():
        return

    # ── Render sidebar + route to page ──
    render_sidebar()
    page = st.session_state.get("current_page", "dashboard")

    if   page == "dashboard":   page_dashboard()
    elif page == "record_sale": page_record_sale()
    elif page == "products":    page_products()
    elif page == "expenses":    page_expenses()
    elif page == "insights":    page_insights()
    elif page == "admin":
        if st.session_state.user.get("role") == "admin":
            page_admin()
        else:
            st.error("Access denied.")
    else:
        page_dashboard()


if __name__ == "__main__":
    main()
