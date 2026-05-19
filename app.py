# Rice Market — Streamlit MVP (Single File App)

```python
import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import gspread
from google.oauth2.service_account import Credentials

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Rice Market",
    page_icon="🌾",
    layout="wide"
)

# =========================================================
# STYLING
# =========================================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }

    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        text-align: center;
    }

    .title {
        font-size: 2.5rem;
        font-weight: bold;
        color: #166534;
    }

    .subtitle {
        color: #475569;
        margin-bottom: 30px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# GOOGLE SHEETS CONNECTION
# =========================================================
def connect_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(creds)
    sheet = client.open(st.secrets["sheet_name"])

    return sheet


sheet = connect_gsheet()

inventory_ws = sheet.worksheet("inventory")
orders_ws = sheet.worksheet("orders")
hubs_ws = sheet.worksheet("pickup_hubs")

# =========================================================
# LOAD DATA
# =========================================================
def load_inventory():
    data = inventory_ws.get_all_records()
    return pd.DataFrame(data)


def load_orders():
    data = orders_ws.get_all_records()
    return pd.DataFrame(data)


def load_hubs():
    data = hubs_ws.get_all_records()
    return pd.DataFrame(data)


inventory_df = load_inventory()
orders_df = load_orders()
hubs_df = load_hubs()

# =========================================================
# AUTHENTICATION
# =========================================================
def load_users():
    try:
        users_ws = sheet.worksheet("users")
        data = users_ws.get_all_records()
        return pd.DataFrame(data), users_ws
    except:
        users_ws = sheet.add_worksheet(title="users", rows=1000, cols=10)

        users_ws.append_row([
            "user_id",
            "full_name",
            "email",
            "phone",
            "password",
            "created_at"
        ])

        return pd.DataFrame(), users_ws


users_df, users_ws = load_users()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = None


def register_user(full_name, email, phone, password):

    existing = users_df[
        users_df["email"].astype(str).str.lower() == email.lower()
    ]

    if not existing.empty:
        return False, "Email already exists"

    user_id = str(uuid.uuid4())[:8]

    users_ws.append_row([
        user_id,
        full_name,
        email,
        phone,
        password,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    return True, "Registration successful"


def login_user(email, password):

    if users_df.empty:
        return False

    result = users_df[
        (users_df["email"].astype(str).str.lower() == email.lower())
        &
        (users_df["password"].astype(str) == password)
    ]

    return not result.empty


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.title("🌾 Rice Market")

if not st.session_state.logged_in:

    auth_option = st.sidebar.selectbox(
        "Authentication",
        ["Login", "Register"]
    )

    # =============================================
    # REGISTER
    # =============================================
    if auth_option == "Register":

        st.title("📝 Create Account")

        with st.form("register_form"):

            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            password = st.text_input("Password", type="password")

            register_btn = st.form_submit_button("Register")

            if register_btn:

                success, message = register_user(
                    full_name,
                    email,
                    phone,
                    password
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)

    # =============================================
    # LOGIN
    # =============================================
    else:

        st.title("🔐 Login")

        with st.form("login_form"):

            login_email = st.text_input("Email")
            login_password = st.text_input("Password", type="password")

            login_btn = st.form_submit_button("Login")

            if login_btn:

                valid = login_user(login_email, login_password)

                if valid:
                    st.session_state.logged_in = True
                    st.session_state.user_email = login_email
                    st.success("Login successful")
                    st.rerun()
                else:
                    st.error("Invalid email or password")

    st.stop()

st.sidebar.success(f"Logged in: {st.session_state.user_email}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_email = None
    st.rerun()

page = st.sidebar.radio(
    "Navigation",
    [
        "Home",
        "Market Prices",
        "Place Order",
        "Track Orders",
        "Admin Dashboard"
    ]
)

# =========================================================
# HOME PAGE
# =========================================================
if page == "Home":

    st.markdown('<div class="title">Rice Market</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Transparent Rice Pricing & Strategic Pickup Marketplace</div>',
        unsafe_allow_html=True
    )

    total_products = len(inventory_df)
    total_orders = len(orders_df)
    total_hubs = len(hubs_df)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rice Products", total_products)

    with col2:
        st.metric("Orders", total_orders)

    with col3:
        st.metric("Pickup Hubs", total_hubs)

    st.markdown("---")

    st.subheader("Available Rice Products")

    if not inventory_df.empty:
        st.dataframe(inventory_df, use_container_width=True)
    else:
        st.warning("No inventory available")

# =========================================================
# MARKET PRICES
# =========================================================
elif page == "Market Prices":

    st.title("📈 Current Market Prices")

    if inventory_df.empty:
        st.warning("No inventory data available")
    else:

        search = st.text_input("Search rice type")

        filtered_df = inventory_df.copy()

        if search:
            filtered_df = filtered_df[
                filtered_df["rice_name"].astype(str).str.contains(search, case=False)
            ]

        st.dataframe(filtered_df, use_container_width=True)

# =========================================================
# PLACE ORDER
# =========================================================
elif page == "Place Order":

    st.title("🛒 Place Order")

    if inventory_df.empty:
        st.warning("No products available")
    else:

        with st.form("order_form"):

            customer_name = st.text_input("Full Name")
            phone = st.text_input("Phone Number")

            rice_options = inventory_df["rice_name"].tolist()
            selected_rice = st.selectbox("Select Rice", rice_options)

            quantity = st.number_input(
                "Quantity (Bags)",
                min_value=1,
                value=1
            )

            pickup_options = hubs_df["hub_name"].tolist()
            pickup_hub = st.selectbox("Pickup Location", pickup_options)

            payment_method = st.selectbox(
                "Payment Method",
                ["Bank Transfer", "Cash", "Pay on Pickup"]
            )

            submit = st.form_submit_button("Place Order")

            if submit:

                selected_row = inventory_df[
                    inventory_df["rice_name"] == selected_rice
                ].iloc[0]

                unit_price = float(selected_row["price_per_bag"])
                total_amount = quantity * unit_price

                order_id = str(uuid.uuid4())[:8]

                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                new_order = [
                    order_id,
                    customer_name,
                    phone,
                    selected_rice,
                    quantity,
                    pickup_hub,
                    payment_method,
                    total_amount,
                    "Pending",
                    "Pending",
                    created_at
                ]

                orders_ws.append_row(new_order)

                st.success("Order placed successfully!")

                st.info(f"Order ID: {order_id}")
                st.info(f"Total Amount: ₦{total_amount:,.0f}")

# =========================================================
# TRACK ORDERS
# =========================================================
elif page == "Track Orders":

    st.title("📦 Track Orders")

    order_search = st.text_input("Enter Order ID")

    if order_search:

        result = orders_df[
            orders_df["order_id"].astype(str) == order_search
        ]

        if result.empty:
            st.error("Order not found")
        else:
            st.success("Order Found")
            st.dataframe(result, use_container_width=True)

# =========================================================
# ADMIN DASHBOARD
# =========================================================
elif page == "Admin Dashboard":

    st.title("⚙️ Admin Dashboard")

    admin_password = st.text_input(
        "Enter Admin Password",
        type="password"
    )

    if admin_password == st.secrets["admin_password"]:

        tabs = st.tabs([
            "Inventory",
            "Orders",
            "Pickup Hubs"
        ])

        # =============================================
        # INVENTORY TAB
        # =============================================
        with tabs[0]:

            st.subheader("Inventory Management")

            st.dataframe(inventory_df, use_container_width=True)

            st.markdown("---")
            st.subheader("Add New Rice Product")

            with st.form("inventory_form"):

                rice_id = str(uuid.uuid4())[:6]

                rice_name = st.text_input("Rice Name")
                category = st.selectbox(
                    "Category",
                    ["Local", "Imported", "Premium"]
                )

                price_per_bag = st.number_input(
                    "Price Per Bag",
                    min_value=0
                )

                available_quantity = st.number_input(
                    "Available Quantity",
                    min_value=0
                )

                location = st.text_input("Location")

                submit_inventory = st.form_submit_button("Add Product")

                if submit_inventory:

                    inventory_ws.append_row([
                        rice_id,
                        rice_name,
                        category,
                        price_per_bag,
                        available_quantity,
                        location,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ])

                    st.success("Product added successfully")

        # =============================================
        # ORDERS TAB
        # =============================================
        with tabs[1]:

            st.subheader("Orders")

            st.dataframe(orders_df, use_container_width=True)

        # =============================================
        # HUBS TAB
        # =============================================
        with tabs[2]:

            st.subheader("Pickup Hubs")

            st.dataframe(hubs_df, use_container_width=True)

            st.markdown("---")
            st.subheader("Add Pickup Hub")

            with st.form("hub_form"):

                hub_id = str(uuid.uuid4())[:6]

                hub_name = st.text_input("Hub Name")
                address = st.text_input("Address")
                city = st.text_input("City")
                contact_person = st.text_input("Contact Person")
                phone = st.text_input("Phone")

                submit_hub = st.form_submit_button("Add Hub")

                if submit_hub:

                    hubs_ws.append_row([
                        hub_id,
                        hub_name,
                        address,
                        city,
                        contact_person,
                        phone
                    ])

                    st.success("Pickup hub added successfully")

    else:
        st.warning("Enter admin password to continue")
```

---

# Requirements.txt

```txt
streamlit
pandas
gspread
google-auth
```

---

# Google Sheet Setup

Create ONE Google Sheet called:

```txt
RiceMarketDB
```

Create these worksheets inside it:

## 1. users

```txt
user_id
full_name
email
phone
password
created_at
```

---

## 2. inventory

```txt
rice_id
rice_name
category
price_per_bag
available_quantity
location
updated_at
```

---

## 3. orders

```txt
order_id
customer_name
phone
rice_name
quantity
pickup_hub
payment_method
total_amount
payment_status
order_status
created_at
```

---

## 4. pickup_hubs

```txt
hub_id
hub_name
address
city
contact_person
phone
```

---

# Streamlit Secrets Setup

Create:

```txt
.streamlit/secrets.toml
```

Add:

```toml
admin_password = "admin123"
sheet_name = "RiceMarketDB"

[gcp_service_account]
type = "service_account"
project_id = "YOUR_PROJECT_ID"
private_key_id = "YOUR_PRIVATE_KEY_ID"
private_key = "YOUR_PRIVATE_KEY"
client_email = "YOUR_CLIENT_EMAIL"
client_id = "YOUR_CLIENT_ID"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "YOUR_CERT_URL"
```

---

# Deployment Steps

## Step 1

Push code to GitHub.

---

## Step 2

Go to:

```txt
https://share.streamlit.io
```

---

## Step 3

Connect GitHub repo.

---

## Step 4

Deploy app.

---

## Step 5

Add secrets in Streamlit Cloud:

```txt
App Settings → Secrets
```

Paste your secrets.toml content.

---

# Future Improvements

## Add:

* Paystack payment integration
* WhatsApp notifications
* SMS alerts
* Supplier dashboard
* Delivery tracking
* Analytics dashboard
* Customer accounts
* AI price prediction
* Bulk order system
* Warehouse management

---

# MVP Goal

DO NOT overbuild.

Your first goal is:

* launch fast
* test demand
* onboard suppliers
* validate pickup operations
* get first customers
* refine logistics

