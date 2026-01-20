import asyncio, os
from email.message import EmailMessage
import aiosmtplib
from dotenv import load_dotenv

load_dotenv()

async def test():
    msg = EmailMessage()
    msg["From"] = os.getenv("MAIL_FROM")
    msg["To"] = os.getenv("SMTP_USER")
    msg["Subject"] = "Invigilink-AI SMTP Test"
    msg.set_content("✅ SMTP configuration working correctly!")

    await aiosmtplib.send(
        msg,
        hostname=os.getenv("SMTP_HOST"),
        port=int(os.getenv("SMTP_PORT")),
        username=os.getenv("SMTP_USER"),
        password=os.getenv("SMTP_PASS"),
        start_tls=True,
    )

asyncio.run(test())
