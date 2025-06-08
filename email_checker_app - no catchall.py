import streamlit as st
import pandas as pd
import time
from email_validator import validate_email, EmailNotValidError
import dns.resolver

DISPOSABLE_DOMAINS = {'mailinator.com', '10minutemail.com', 'tempmail.com', 'yopmail.com'}
TYPO_DOMAINS = {'gamil.com', 'yaho.com', 'hotnail.com'}

def has_mx_record(domain):
    try:
        dns.resolver.resolve(domain, 'MX')
        return True
    except Exception:
        return False

def check_email(email):
    email = email.strip().replace(';', '')  # Clean email
    result = {
        'email': email,
        'validation_status': '',
        'validation_analysis': ''
    }

    try:
        valid = validate_email(email)
        domain = valid['domain']
        has_mx = has_mx_record(domain)

        if not has_mx:
            result['validation_status'] = 'Do Not Send'
            result['validation_analysis'] = 'No MX'
        elif domain.lower() in DISPOSABLE_DOMAINS:
            result['validation_status'] = 'Do Not Send'
            result['validation_analysis'] = 'Disposable'
        else:
            result['validation_status'] = 'Okay to Send'
            result['validation_analysis'] = 'Accepted'

    except EmailNotValidError:
        result['validation_status'] = 'Do Not Send'
        result['validation_analysis'] = 'Invalid Syntax'

    return result


    try:
        valid = validate_email(email)
        domain = valid['domain']
        result['is_valid'] = True
    except EmailNotValidError:
        result['risk_flag'] = 'invalid_syntax'
        return result

    domain_lower = domain.lower()

    if domain_lower in DISPOSABLE_DOMAINS:
        result['is_disposable'] = True
        result['risk_flag'] = 'disposable'

    if domain_lower in TYPO_DOMAINS:
        result['risk_flag'] = 'possible_typo'

    if has_mx_record(domain_lower):
        result['has_mx'] = True
    else:
        result['risk_flag'] = 'no_mx'

    return result

# Streamlit UI
st.set_page_config(page_title="Local Email Checker", layout="centered")
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
        with st.spinner("Checking..."):
            for email in emails:
                checked_results.append(check_email(email))
                time.sleep(0.5)  # Safety delay

        result_df = pd.DataFrame(checked_results)
        st.success("Done! See below 👇")

        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Results CSV", csv, "checked_emails.csv", "text/csv")
