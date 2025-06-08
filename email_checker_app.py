import streamlit as st
import pandas as pd
import time
from email_validator import validate_email, EmailNotValidError
import dns.resolver
import smtplib
import socket
import random
import string

checked_domains = {}  # cache for unique domain results

def is_catch_all(domain):
    if domain in checked_domains:
        return checked_domains[domain]

    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        if not mx_records:
            checked_domains[domain] = False
            return False

        mail_server = str(mx_records[0].exchange).strip('.')

        server = smtplib.SMTP(timeout=10)
        server.connect(mail_server)
        server.helo("test.local")
        server.mail("test@" + domain)

        fake_user = ''.join(random.choices(string.ascii_lowercase + string.digits, k=24))
        code, message = server.rcpt(f"{fake_user}@{domain}")
        server.quit()

        if code == 250:
            result = 'maybe'
        elif code == 550:
            result = False
        else:
            result = False

    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN,
            socket.gaierror, socket.timeout,
            smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected,
            smtplib.SMTPRecipientsRefused, Exception):
        result = False

    checked_domains[domain] = result
    return result

def status_icon(status):
    if status == "Okay to Send":
        return "🟢 " + status
    elif status == "Do Not Send":
        return "🔴 " + status
    elif status == "Maybe Send":
        return "🟠 " + status
    elif status == "Checking...":
        return "🕐 " + status
    else:
        return status

DISPOSABLE_DOMAINS = {'mailinator.com', '10minutemail.com', 'tempmail.com', 'yopmail.com'}
TYPO_DOMAINS = {'gamil.com', 'yaho.com', 'hotnail.com'}

def has_mx_record(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False

def check_email(email):
    email = email.strip().replace(';', '')
    result = {
        'email': email,
        'validation_status': '',
        'validation_analysis': ''
    }

    try:
        valid = validate_email(email, check_deliverability=False)
        domain = valid['domain'].lower()
    except EmailNotValidError:
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'Invalid Syntax'
        return result

    if not has_mx_record(domain):
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'No MX'
    elif domain in DISPOSABLE_DOMAINS:
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'Disposable'
    elif is_catch_all(domain) == 'maybe':
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'Catch-All'
    elif is_catch_all(domain):
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'Catch-All'
    else:
        result['validation_status'] = 'Okay to Send'
        result['validation_analysis'] = 'Accepted'

    return result

# Streamlit UI
st.set_page_config(page_title="Local Email Checker", layout="wide")
st.sidebar.title("📋 Menu")
selection = st.sidebar.radio("Navigate to", ["Email Validator", "How it Works"])

if selection == "How it Works":
    st.title("📘 How This App Works")
    st.markdown("""
    This tool checks the health of email addresses without storing or sharing any data. 

    When you upload or paste a list of emails, it:
    - Validates basic syntax
    - Checks MX records
    - Detects catch-all domains
    - Flags disposable or risky domains

    All processing happens live, and no data is saved after validation.
    """)

    st.subheader("📄 CSV Format Guide")
    st.markdown("""
    - Your CSV must have a single column named `email`
    - No header row needed if you upload your own list
    - Sample format:

        ```csv
        email
        test@example.com
        hello@domain.com
        info@company.org
        ```
    """)

    st.subheader("🚀 App Features")
    st.markdown("""
    - ✅ Validates email format
    - 📬 Checks domain MX records
    - 🛡️ Detects catch-all mail servers
    - 🔍 Screens out disposable and temporary emails
    - 🧪 Risk-flagging logic with clear icon indicators
    - 🔒 Fully private — we do not collect or store your data
    - 💾 Download results as CSV
    
    ---
    ☕ If this tool helped you, consider [buying me a coffee](https://buymeacoffee.com/nimaa) 🙏
    """)

else:
    st.title("📧 Local Email Health Checker")

    input_method = st.radio("Choose input method:", ["Upload CSV", "Paste Emails"])

    emails = []

    if input_method == "Upload CSV":
        uploaded_file = st.file_uploader("Upload a CSV file with an 'email' column", type="csv")
        if uploaded_file:
            df = pd.read_csv(uploaded_file, usecols=[0], names=["email"], skiprows=1)
            if 'email' not in df.columns:
                st.error("CSV must have a column named 'email'.")
            else:
                emails = df['email'].dropna().astype(str).str.replace(';', '', regex=False).str.strip().tolist()

    elif input_method == "Paste Emails":
        pasted = st.text_area("Paste email addresses (one per line)")
        if pasted.strip():
            emails = [line.strip() for line in pasted.strip().split('\n') if line.strip()]

    if emails:
        if st.button("Check Emails"):
            checked_results = []
            progress_bar = st.progress(0)
            status_placeholder = st.empty()

            for idx, email in enumerate(emails):
                progress = int((idx + 1) / len(emails) * 100)
                progress_bar.progress(progress)

                loading_result = {
                    'email': email,
                    'validation_status': 'Checking...',
                    'validation_analysis': ''
                }
                live_df = pd.DataFrame(checked_results + [loading_result])
                live_df['validation_status'] = live_df['validation_status'].apply(status_icon)
                status_placeholder.dataframe(live_df)

                result = check_email(email)
                checked_results.append(result)
                time.sleep(1)

            st.success("✅ Done!")
            final_df = pd.DataFrame(checked_results)
            final_df['validation_status'] = final_df['validation_status'].apply(status_icon)
            st.dataframe(final_df)

            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Results CSV", data=csv, file_name='checked_emails.csv', mime='text/csv')
