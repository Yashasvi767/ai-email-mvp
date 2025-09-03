# Stub email sender. Does NOT send real emails.
# Replace with SMTP or provider API in production.

def send_email_stub(to_address: str, body: str):
    # write to a local file for audit
    with open("data/sent_emails.log", "a", encoding="utf-8") as f:
        f.write(f"TO: {to_address}\nTIME: {__import__('datetime').datetime.utcnow().isoformat()}\n\n{body}\n{'-'*60}\n")
    return True
