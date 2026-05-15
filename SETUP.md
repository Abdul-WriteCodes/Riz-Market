# BizPulse — Setup Guide
## From Zero to Live in 30 Minutes

---

## STEP 1: Google Cloud Setup (10 mins)

### 1.1 Create a Google Cloud Project
1. Go to https://console.cloud.google.com
2. Click **"New Project"** → name it `bizpulse`
3. Click **"Create"**

### 1.2 Enable Required APIs
In your project, go to **APIs & Services → Library** and enable:
- ✅ **Google Sheets API**
- ✅ **Google Drive API**

### 1.3 Create a Service Account
1. Go to **APIs & Services → Credentials**
2. Click **"Create Credentials" → "Service Account"**
3. Name it `bizpulse-service` → click **"Create and Continue"**
4. Grant role: **"Editor"** → click **"Done"**

### 1.4 Download Credentials JSON
1. Click on your new service account
2. Go to **"Keys"** tab → **"Add Key" → "Create new key"**
3. Choose **JSON** → Download
4. Open the file — you'll need its contents for `secrets.toml`

---

## STEP 2: Google Sheets Setup (5 mins)

### 2.1 Create the Spreadsheet
1. Go to https://sheets.google.com
2. Create a new spreadsheet named **"BizPulse Database"**
3. Copy the Sheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/`**`THIS_IS_YOUR_SHEET_ID`**`/edit`

### 2.2 Create the 4 Sheet Tabs
Rename "Sheet1" and add 3 more tabs. Name them exactly:
- `USERS`
- `PRODUCTS`
- `SALES`
- `EXPENSES`

### 2.3 Add Headers to Each Tab

**USERS tab — Row 1:**
```
user_id | business_id | business_name | full_name | email | password_hash | role | plan_type | plan_status | subscription_start | subscription_end | created_at
```

**PRODUCTS tab — Row 1:**
```
product_id | business_id | product_name | category | cost_price | selling_price | stock_quantity | reorder_level | created_at
```

**SALES tab — Row 1:**
```
sale_id | business_id | product_id | product_name | quantity | unit_price | total_amount | cost_total | gross_profit | payment_method | sale_date | recorded_by
```

**EXPENSES tab — Row 1:**
```
expense_id | business_id | expense_name | category | amount | expense_date | recorded_by
```

### 2.4 Share the Spreadsheet
1. Click **"Share"** in Google Sheets
2. Add your service account email (from the JSON file, field: `client_email`)
3. Set permission to **"Editor"**
4. Click **"Share"**

---

## STEP 3: Configure secrets.toml (5 mins)

Open `.streamlit/secrets.toml` and fill in your values:

```toml
[google_sheets]
sheet_id = "PASTE_YOUR_SHEET_ID_HERE"

[google_credentials]
type = "service_account"
project_id = "your-project-id"           # from JSON file
private_key_id = "your-key-id"           # from JSON file
private_key = "-----BEGIN RSA PRIVATE KEY-----\nXXXXXX\n-----END RSA PRIVATE KEY-----\n"
client_email = "bizpulse-service@your-project.iam.gserviceaccount.com"
client_id = "123456789"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."

[admin]
email = "your-admin-email@gmail.com"
password = "choose-a-strong-admin-password"
business_id = "ADMIN"
```

⚠️ **Important:** Copy the `private_key` exactly from the JSON file.
Replace actual newlines with `\n` if needed.

---

## STEP 4: Update Payment Details in app.py (2 mins)

Find `PAYMENT_DETAILS` near the top of `app.py` and update:

```python
PAYMENT_DETAILS = {
    "bank":           "Your Actual Bank Name",
    "account_name":   "Your Business Name",
    "account_number": "YOUR_ACCOUNT_NUMBER",
    "monthly_price":  1000,
    "yearly_price":   10000,
    "trial_days":     14,
}
```

---

## STEP 5: Run Locally (2 mins)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

Visit http://localhost:8501 in your browser.

**Test with admin login:**
- Email: (whatever you set in secrets.toml)
- Password: (whatever you set in secrets.toml)

---

## STEP 6: Deploy to Streamlit Community Cloud (5 mins)

1. Push your code to a **GitHub repository** (make sure `.streamlit/secrets.toml` is in `.gitignore`)
2. Go to https://share.streamlit.io
3. Click **"New app"**
4. Connect your GitHub repo → select `app.py`
5. Click **"Advanced settings"** → paste your `secrets.toml` contents
6. Click **"Deploy"**

Your app will be live at: `https://your-app-name.streamlit.app`

---

## ADMIN WORKFLOW: Activating Users

When a business signs up for a paid plan:

1. They transfer money to your bank account using their email as reference
2. Check your bank alerts
3. Log in to BizPulse with your admin credentials
4. Go to **Admin Panel → Pending Activation**
5. Find their account → click **"✅ Activate"**
6. They can now log in with full access

---

## FILE STRUCTURE

```
bizpulse/
├── app.py                    ← Entire application (single file)
├── requirements.txt          ← Python dependencies
├── SETUP.md                  ← This guide
└── .streamlit/
    └── secrets.toml          ← Your credentials (NEVER commit this)
```

---

## IMPORTANT: Security Checklist

- [ ] `secrets.toml` is in `.gitignore`
- [ ] Admin password is strong (12+ chars, mixed)
- [ ] Service account only has Editor access (not Owner)
- [ ] Google Sheet is shared only with the service account email
- [ ] Test a full signup → sale → dashboard flow before going live

---

## TROUBLESHOOTING

**"Error reading USERS"**
→ Check that tab names match exactly: USERS, PRODUCTS, SALES, EXPENSES
→ Verify the sheet is shared with your service account email

**"Invalid credentials"**
→ Make sure `private_key` in secrets.toml preserves `\n` line breaks

**Login not working**
→ Check admin email/password match secrets.toml exactly

**Charts not showing**
→ You need at least one sale recorded first

---

## NEXT STEPS (V2 Roadmap)

- [ ] Add Flutterwave for automatic payment collection
- [ ] Email notifications for low stock alerts
- [ ] SMS alerts via Termii or Twilio
- [ ] Staff accounts per business
- [ ] Migrate database to Supabase when you hit 300 users
- [ ] Mobile app wrapper via Streamlit + PWA
