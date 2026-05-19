import streamlit as st
import pandas as pd
from datetime import datetime
import uuid
import gspread
from google.oauth2.service_account import Credentials

# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="Rice Market",
    page_icon="🌾",
    layout="wide"
)

# ======================================================
# CUSTOM STYLING
# ======================================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f8fafc;
    }

    .stButton > button {
        width: 100%;
        border-radius: 10px;
        height: 45px;
        background-color: #166534;
        color: white;
        border: none;
        font-weight: bold;
    }

    .stButton > button:hover {
        background-color: #14532d;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# GOOGLE SHEETS CONNECTION
# ======================================================
@st.cache_resource
def connect_google_sheet():

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open(st.secrets["sheet_name"])

    return spreadsheet


sheet = connect_google_sheet()

# ======================================================
# WORKSHEETS
# ======================================================
users_ws = sheet.worksheet("users")
inventory_ws = sheet.worksheet("inventory")
orders_ws = sheet.worksheet("orders")
pickup_ws = sheet.worksheet("pickup_hubs")

# ======================================================
# LOAD DATA
# ======================================================
def load_data(worksheet):
    data = worksheet.get_all_records()
    return pd.DataFrame(data)


users_df = load_data(users_ws)
inventory_df = load_data(inventory_ws)
orders_df = load_data(orders_ws)
pickup_df = load_data(pickup_ws)

# ======================================================
# SESSION STATE
# ======================================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# ======================================================
# AUTH FUNCTIONS
# ======================================================
def register_user(full_name, email, phone, password):

    if not users_df.empty:

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

# ======================================================
# AUTH SCREEN
# ======================================================
if not st.session_state.logged_in:

    st.title("🌾 Rice Market")
    st.caption("Transparent Rice Pricing & Strategic Pickup Platform")

    auth_tab1, auth_tab2 = st.tabs(["Login", "Register"])

    # ==================================================
    # LOGIN
    # ==================================================
    with auth_tab1:

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
                    st.error("Invalid credentials")

    # ==================================================
    # REGISTER
    # ==================================================
    with auth_tab2:

        with st.form("register_form"):

            full_name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number")
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

    st.stop()

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.title("🌾 Rice Market")
st.sidebar.success(f"Logged in as: {st.session_state.user_email}")

if st.sidebar.button("Logout"):
    st.session_state.logged_in = False
    st.session_state.user_email = ""
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

# ======================================================
# HOME PAGE
# ======================================================
if page == "Home":

    st.title("🌾 Rice Market")
    st.caption("Buy Rice At Transparent Market Prices")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Rice Products", len(inventory_df))

    with col2:
        st.metric("Orders", len(orders_df))

    with col3:
        st.metric("Pickup Hubs", len(pickup_df))

    st.markdown("---")

    st.subheader("Available Rice Products")

    if inventory_df.empty:
        st.warning("No inventory available")
    else:
        st.dataframe(inventory_df, use_container_width=True)

# ======================================================
# MARKET PRICES
# ======================================================
elif page == "Market Prices":

    st.title("📈 Current Rice Prices")

    if inventory_df.empty:
        st.warning("No inventory data available")

    else:

        search = st.text_input("Search Rice")

        filtered_df = inventory_df.copy()

        if search:
            filtered_df = filtered_df[
                filtered_df["rice_name"].astype(str).str.contains(search, case=False)
            ]

        st.dataframe(filtered_df, use_container_width=True)

# ======================================================
# PLACE ORDER
# ======================================================
elif page == "Place Order":

    st.title("🛒 Place Order")

    if inventory_df.empty:
        st.warning("No rice products available")

    else:

        with st.form("order_form"):

            rice_options = inventory_df["rice_name"].tolist()
            selected_rice = st.selectbox("Select Rice", rice_options)

            quantity = st.number_input(
                "Quantity (Bags)",
                min_value=1,
                value=1
            )

            pickup_options = pickup_df["hub_name"].tolist()
            selected_hub = st.selectbox(
                "Pickup Hub",
                pickup_options
            )

            payment_method = st.selectbox(
                "Payment Method",
                ["Bank Transfer", "Cash", "Pay On Pickup"]
            )

            submit_order = st.form_submit_button("Place Order")

            if submit_order:

                selected_row = inventory_df[
                    inventory_df["rice_name"] == selected_rice
                ].iloc[0]

                unit_price = float(selected_row["price_per_bag"])
                total_amount = unit_price * quantity

                order_id = str(uuid.uuid4())[:8]

                new_order = [
                    order_id,
                    st.session_state.user_email,
                    selected_rice,
                    quantity,
                    selected_hub,
                    payment_method,
                    total_amount,
                    "Pending",
                    "Pending",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ]

                orders_ws.append_row(new_order)

                st.success("Order placed successfully")
                st.info(f"Order ID: {order_id}")
                st.info(f"Total Amount: ₦{total_amount:,.0f}")

# ======================================================
# TRACK ORDERS
# ======================================================
elif page == "Track Orders":

    st.title("📦 Track Orders")

    if orders_df.empty:
        st.warning("No orders available")

    else:

        user_orders = orders_df[
            orders_df["customer_email"].astype(str) == st.session_state.user_email
        ]

        if user_orders.empty:
            st.info("You have no orders yet")
        else:
            st.dataframe(user_orders, use_container_width=True)

# ======================================================
# ADMIN DASHBOARD
# ======================================================
elif page == "Admin Dashboard":

    st.title("⚙️ Admin Dashboard")

    admin_password = st.text_input(
        "Admin Password",
        type="password"
    )

    if admin_password == st.secrets["admin_password"]:

        admin_tab1, admin_tab2, admin_tab3 = st.tabs([
            "Inventory",
            "Orders",
            "Pickup Hubs"
        ])

        # ==================================================
        # INVENTORY
        # ==================================================
        with admin_tab1:

            st.subheader("Inventory")
            st.dataframe(inventory_df, use_container_width=True)

            st.markdown("---")
            st.subheader("Add New Product")

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

                add_product = st.form_submit_button("Add Product")

                if add_product:

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

        # ==================================================
        # ORDERS
        # ==================================================
        with admin_tab2:

            st.subheader("Orders")
            st.dataframe(orders_df, use_container_width=True)

        # ==================================================
        # PICKUP HUBS
        # ==================================================
        with admin_tab3:

            st.subheader("Pickup Hubs")
            st.dataframe(pickup_df, use_container_width=True)

            st.markdown("---")
            st.subheader("Add Pickup Hub")

            with st.form("hub_form"):

                hub_id = str(uuid.uuid4())[:6]

                hub_name = st.text_input("Hub Name")
                address = st.text_input("Address")
                city = st.text_input("City")
                contact_person = st.text_input("Contact Person")
                phone = st.text_input("Phone")

                add_hub = st.form_submit_button("Add Hub")

                if add_hub:

                    pickup_ws.append_row([
                        hub_id,
                        hub_name,
                        address,
                        city,
                        contact_person,
                        phone
                    ])

                    st.success("Pickup hub added successfully")

    else:
        st.warning("Enter correct admin password")
