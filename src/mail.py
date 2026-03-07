import smtplib
from email.message import EmailMessage

import pandas as pd


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


def build_email_html(df: pd.DataFrame, intro: str) -> str:
    th_style = 'style="font-family:Arial,sans-serif;font-size:14px;color:#222;background-color:#ffffff;padding:10px 12px;border-bottom:2px solid #333;text-align:left;font-weight:bold;"'
    td_style = 'style="font-family:Arial,sans-serif;font-size:14px;color:#444;background-color:#ffffff;padding:10px 12px;border-bottom:1px solid #dddddd;"'

    header_cells = "".join(f"<th {th_style}>{col}</th>" for col in df.columns)
    rows = ""
    for _, row in df.iterrows():
        formatted_cells = []
        for val in row:
            if isinstance(val, (int, float)):
                formatted_cells.append(f"<td {td_style}>{val:.2f}</td>")
            else:
                formatted_cells.append(f"<td {td_style}>{val}</td>")
        rows += f"<tr>{''.join(formatted_cells)}</tr>"

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;background-color:#ffffff;padding:16px;">
        <p style="font-family:Arial,sans-serif;font-size:14px;color:#444;">{intro}</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;" cellpadding="0" cellspacing="0">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
