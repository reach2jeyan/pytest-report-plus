import os
import smtplib
from email.message import EmailMessage

def load_email_env(filepath="emailenv"):
    if not os.path.exists(filepath):
        raise FileNotFoundError("emailenv file not found!")

    config = {}
    with open(filepath, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                config[key.strip()] = value.strip()
    return config

def send_email_from_env(config: dict):
    sender = config["sender_email"]
    recipient = config["recipient_email"]
    report_path = config["report_path"]
    subject = config["subject"]
    smtp_server = config["smtp_server"]
    smtp_port = int(config["smtp_port"])
    password = config["email_password"]
    use_tls = True

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient

    # Read report content
    with open(report_path, "r") as f:
        html_content = f.read()

    msg.set_content("Your test report is attached.")
    msg.add_alternative(html_content, subtype="html")

    try:
        if "sendgrid" in smtp_server.lower():
            if not password.startswith("SG."):
                print("****************************************************************")
                print("SendGrid API key looks invalid. It should start with 'SG.'")
                print("****************************************************************")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            if use_tls:
                server.starttls()
            login_user = "apikey" if "sendgrid" in smtp_server.lower() else sender
            server.login(login_user, password)
            server.send_message(msg)
            server.quit()
            print("****************************************************************")
            print(f"{subject} is sent to {recipient} from {sender} successfully")
            print("****************************************************************")
    except Exception as e:
        print(f"Failed to send email: {e}")


