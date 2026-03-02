"""
Email service for sending OTP codes via Mailtrap API or SMTP fallback
"""
import asyncio
import aiosmtplib
import mailtrap as mt
from email.message import EmailMessage
from app.core.config import settings
from typing import Optional


def _get_mailtrap_client() -> Optional[mt.MailtrapClient]:
    """
    Initialize and return Mailtrap client if configured.

    Returns:
        MailtrapClient instance if configured, None otherwise
    """
    if not settings.MAILTRAP_API_TOKEN:
        return None

    return mt.MailtrapClient(
        token=settings.MAILTRAP_API_TOKEN,
        sandbox=settings.MAILTRAP_USE_SANDBOX,
        inbox_id=settings.MAILTRAP_INBOX_ID if settings.MAILTRAP_USE_SANDBOX else None,
    )


def _get_html_body(code: str) -> str:
    """
    Generate HTML email body for OTP code.

    Args:
        code: 6-digit OTP code

    Returns:
        HTML string for email body
    """
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
    </head>
    <body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f5f5f5;">
        <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%" style="background-color: #f5f5f5;">
            <tr>
                <td align="center" style="padding: 40px 20px;">
                    <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="600" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="padding: 40px 40px 30px 40px; text-align: center; border-bottom: 1px solid #e5e7eb;">
                                <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #111827; letter-spacing: -0.5px;">
                                    Verification Code
                                </h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 40px 30px 40px;">
                                <p style="margin: 0 0 20px 0; font-size: 16px; line-height: 24px; color: #374151;">
                                    Hello,
                                </p>
                                <p style="margin: 0 0 30px 0; font-size: 16px; line-height: 24px; color: #374151;">
                                    You've requested a verification code to access your account. Use the code below to complete your login:
                                </p>
                                
                                <!-- OTP Code Box -->
                                <table role="presentation" cellspacing="0" cellpadding="0" border="0" width="100%">
                                    <tr>
                                        <td align="center" style="padding: 20px 0 30px 0;">
                                            <div style="display: inline-block; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2px; border-radius: 12px;">
                                                <div style="background-color: #ffffff; padding: 24px 32px; border-radius: 10px;">
                                                    <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #111827; font-family: 'Courier New', monospace; text-align: center;">
                                                        {code}
                                                    </div>
                                                </div>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 20px; color: #6b7280; text-align: center;">
                                    This code will expire in <strong style="color: #374151;">{settings.OTP_EXPIRY_MINUTES} minutes</strong>.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="padding: 30px 40px 40px 40px; background-color: #f9fafb; border-top: 1px solid #e5e7eb; border-radius: 0 0 8px 8px;">
                                <p style="margin: 0 0 10px 0; font-size: 13px; line-height: 18px; color: #6b7280; text-align: center;">
                                    If you didn't request this code, please ignore this email or contact support if you have concerns.
                                </p>
                                <p style="margin: 0; font-size: 12px; line-height: 18px; color: #9ca3af; text-align: center;">
                                    © Sourcio. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


async def _send_via_mailtrap(email: str, code: str) -> bool:
    """
    Send OTP email via Mailtrap API.

    Args:
        email: Recipient email address
        code: 6-digit OTP code

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        client = _get_mailtrap_client()
        if not client:
            return False

        # Determine sender email and name
        sender_email = settings.MAILTRAP_FROM_EMAIL or settings.SMTP_FROM_EMAIL or "noreply@sourcio.com"
        sender_name = settings.MAILTRAP_FROM_NAME or "Sourcio"

        # Create mail object
        mail = mt.Mail(
            sender=mt.Address(email=sender_email, name=sender_name),
            to=[mt.Address(email=email)],
            subject="Your Verification Code - Sourcio",
            text=f"Your verification code is: {code}\n\nThis code will expire in {settings.OTP_EXPIRY_MINUTES} minutes.",
            html=_get_html_body(code),
            category="OTP Verification",
        )

        # Send email (wrap synchronous call in thread to avoid blocking event loop)
        response = await asyncio.to_thread(client.send, mail)

        # Check if successful
        if response and response.get("success"):
            return True
        else:
            print(f"Mailtrap send failed: {response}")
            return False

    except Exception as e:
        print(f"Error sending email via Mailtrap: {e}")
        return False


async def _send_via_smtp(email: str, code: str) -> bool:
    """
    Send OTP email via SMTP (fallback method).

    Args:
        email: Recipient email address
        code: 6-digit OTP code

    Returns:
        True if email sent successfully, False otherwise
    """
    # Check if SMTP is configured
    if not all([
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.SMTP_FROM_EMAIL
    ]):
        return False

    try:
        # Create email message
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = email
        message["Subject"] = "Your Verification Code - Sourcio"
        message.set_content(_get_html_body(code), subtype="html")

        # Port 465 uses SSL (implicit), port 587 uses STARTTLS (explicit TLS)
        if settings.SMTP_PORT == 465:
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=True,  # Enables SSL/TLS for port 465
            )
        elif settings.SMTP_PORT == 587:
            # Port 587 uses STARTTLS (explicit TLS)
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )
        else:
            # Default behavior for other ports
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )

        return True
    except Exception as e:
        print(f"Error sending email via SMTP: {e}")
        return False


async def send_otp_email(email: str, code: str) -> bool:
    """
    Send OTP code to user's email address.
    Uses Mailtrap API if configured, otherwise falls back to SMTP, 
    otherwise logs to console (for development).

    Args:
        email: Recipient email address
        code: 6-digit OTP code

    Returns:
        True if email sent successfully, False otherwise
    """
    # Try Mailtrap first (if configured)
    if settings.MAILTRAP_API_TOKEN:
        success = await _send_via_mailtrap(email, code)
        if success:
            return True
        # If Mailtrap fails, fall through to SMTP

    # Try SMTP as fallback (if configured)
    if all([
        settings.SMTP_HOST,
        settings.SMTP_PORT,
        settings.SMTP_USER,
        settings.SMTP_PASSWORD,
        settings.SMTP_FROM_EMAIL
    ]):
        success = await _send_via_smtp(email, code)
        if success:
            return True

    # If neither Mailtrap nor SMTP is configured or both failed, log to console (for development)
    print(f"[EMAIL SERVICE] OTP for {email}: {code}")
    return True
