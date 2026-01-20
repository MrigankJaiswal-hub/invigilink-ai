import os, aiosmtplib
from email.message import EmailMessage

SMTP_HOST=os.getenv("SMTP_HOST")
SMTP_PORT=int(os.getenv("SMTP_PORT","587"))
SMTP_USER=os.getenv("SMTP_USER")
SMTP_PASS=os.getenv("SMTP_PASS")
MAIL_FROM=os.getenv("MAIL_FROM","Exam Cell <no-reply@example.com>")
MAIL_CC=os.getenv("MAIL_CC","")  # optional: comma-separated CCs

async def send_mail(to_addr: str, subject: str, html: str, attachments: list[tuple[str, bytes]] = []):
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to_addr
    if MAIL_CC:
        msg["Cc"] = MAIL_CC
    msg["Subject"] = subject
    msg.set_content("This email contains HTML and attachments.")
    msg.add_alternative(html, subtype="html")
    for filename, data in attachments:
        msg.add_attachment(data, maintype="application", subtype="pdf", filename=filename)
    await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True,
                          username=SMTP_USER, password=SMTP_PASS)
