import smtplib
from email.message import EmailMessage


class Mail:
    def __init__(self, config: dict, subject: str, body_html: str) -> None:
        manager = config.get("family_manager", {})
        self.sender = manager.get("email")
        self.password = manager.get("password")

        user_data = config.get("users", {})
        self.to = [
            info["email"]
            for info in user_data.values()
            if info.get("email", "").strip()
        ]

        self.subject = subject
        self.body_html = body_html

    def send(self):
        if not self.sender or not self.password:
            return False, "Manager email/password not configured. Check Settings."
        if not self.to:
            return False, "No recipient emails found. Add emails to users in Settings."

        msg = EmailMessage()
        msg["Subject"] = self.subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.to)

        msg.set_content("Please use an HTML-compatible email client to view this bill.")
        msg.add_alternative(self.body_html, subtype="html")

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender, self.password)
                server.send_message(msg)
        except Exception as e:
            return False, str(e)
        else:
            return True, "Email sent successfully!"
