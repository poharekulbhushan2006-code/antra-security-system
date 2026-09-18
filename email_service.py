import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from config import (
    SMTP_HOST,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SMTP_FROM,
    SMTP_USE_TLS,
    ADMIN_ALERT_EMAIL,
    BANK_NAME,
    TERMINAL_ID,
)
import database

def send_intruder_email_alert(
    photo_path: Path,
    timestamp: str,
    reason: str,
    threat_level: str = "CRITICAL",
    incident_id: Optional[int] = None,
    recipient: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constructs and sends an urgent security email alert with the captured intruder photograph attached.
    If SMTP credentials are not configured, records the alert as 'SIMULATED' for testing.
    """
    target_email = recipient or database.get_setting("admin_alert_email") or ADMIN_ALERT_EMAIL

    # Check if SMTP is configured
    smtp_user = database.get_setting("smtp_user") or SMTP_USER
    smtp_password = database.get_setting("smtp_password") or SMTP_PASSWORD
    smtp_host = database.get_setting("smtp_host") or SMTP_HOST
    smtp_port = int(database.get_setting("smtp_port") or SMTP_PORT)
    smtp_from = database.get_setting("smtp_from") or SMTP_FROM or smtp_user or "security-alerts@aegisvault.local"
    smtp_tls = database.get_setting("smtp_use_tls")
    use_tls = (smtp_tls.lower() in ("true", "1", "yes")) if smtp_tls else SMTP_USE_TLS

    if not smtp_user or not smtp_password:
        print(f"[ALERT NOTIFICATION] (SIMULATED - SMTP NOT CONFIGURED)")
        print(f"  Target: {target_email}")
        print(f"  Incident ID: {incident_id}")
        print(f"  Reason: {reason}")
        print(f"  Evidence Photo: {photo_path}")
        print(f"  To enable real email dispatch, configure SMTP in .env or the Security Dashboard.")
        if incident_id:
            database.update_intruder_email_status(incident_id, status=2, recipient=target_email) # 2 = Simulated / Local
        return {
            "status": "simulated",
            "message": "Alert queued locally. SMTP credentials not yet configured in system.",
            "recipient": target_email
        }

    try:
        msg = MIMEMultipart("related")
        msg["Subject"] = f"🚨 [BREACH ALERT] Unregistered Face Detected - {BANK_NAME}"
        msg["From"] = f"AegisVault Security System <{smtp_from}>"
        msg["To"] = target_email
        msg["X-Priority"] = "1"
        msg["Importance"] = "High"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background-color: #0b0f19; color: #e2e8f0; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #111827; border: 2px solid #ef4444; border-radius: 8px; overflow: hidden; }}
            .header {{ background: #dc2626; color: #ffffff; padding: 20px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 22px; text-transform: uppercase; letter-spacing: 1px; }}
            .content {{ padding: 25px; }}
            .alert-box {{ background: rgba(239, 68, 68, 0.15); border-left: 4px solid #ef4444; padding: 12px 16px; margin-bottom: 20px; border-radius: 4px; }}
            .details-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
            .details-table td {{ padding: 8px 12px; border-bottom: 1px solid #1f2937; font-size: 14px; }}
            .details-table td.label {{ color: #94a3b8; font-weight: bold; width: 35%; }}
            .details-table td.val {{ color: #f8fafc; font-family: monospace; }}
            .photo-box {{ text-align: center; margin: 20px 0; background: #030712; padding: 15px; border-radius: 6px; border: 1px dashed #ef4444; }}
            .photo-box img {{ max-width: 100%; height: auto; border-radius: 4px; border: 2px solid #dc2626; }}
            .footer {{ background: #030712; padding: 15px; text-align: center; font-size: 12px; color: #64748b; }}
            .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; background: #dc2626; color: #fff; font-weight: bold; font-size: 12px; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>⚠️ Vault Access Intrusion Alert</h1>
              <p style="margin: 5px 0 0 0; font-size: 13px;">{BANK_NAME} Security Operations</p>
            </div>
            <div class="content">
              <div class="alert-box">
                <span class="badge">THREAT LEVEL: {threat_level}</span>
                <p style="margin: 8px 0 0 0; font-size: 15px; color: #fca5a5;">
                  <strong>An unregistered or unauthorized person attempted to access the restricted vault!</strong>
                </p>
              </div>

              <table class="details-table">
                <tr><td class="label">Incident ID</td><td class="val">#{incident_id or 'N/A'}</td></tr>
                <tr><td class="label">Terminal Location</td><td class="val">{TERMINAL_ID}</td></tr>
                <tr><td class="label">Timestamp</td><td class="val">{timestamp}</td></tr>
                <tr><td class="label">Detection Reason</td><td class="val">{reason}</td></tr>
                <tr><td class="label">Vault Door Status</td><td class="val" style="color: #ef4444; font-weight: bold;">LOCKED (SECURITY INTERCEPTION ENGAGED)</td></tr>
              </table>

              <div class="photo-box">
                <p style="color: #94a3b8; margin-top: 0; font-size: 13px;">CAPTURED INTRUDER FACIAL SNAPSHOT:</p>
                <img src="cid:intruder_photo" alt="Captured Intruder Evidence">
              </div>

              <p style="font-size: 13px; color: #94a3b8; line-height: 1.5;">
                Recommended Action: Dispatch nearest armed security personnel immediately to {TERMINAL_ID} and review live surveillance feeds.
              </p>
            </div>
            <div class="footer">
              AegisVault Autonomous Biometric Defence System &bull; Confidential Security Dispatch
            </div>
          </div>
        </body>
        </html>
        """

        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)
        msg_alternative.attach(MIMEText(html_body, "html"))

        # Attach Intruder Image with Content-ID for inline preview
        if photo_path and photo_path.exists():
            with open(photo_path, "rb") as f:
                img_data = f.read()
                img = MIMEImage(img_data)
                img.add_header("Content-ID", "<intruder_photo>")
                img.add_header("Content-Disposition", "inline", filename=photo_path.name)
                msg.attach(img)

        # Connect and send
        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

        print(f"✅ Security Email Alert dispatched successfully to {target_email}!")
        if incident_id:
            database.update_intruder_email_status(incident_id, status=1, recipient=target_email)
        database.log_audit(
            event_type="EMAIL_ALERT_SENT",
            status="SUCCESS",
            details=f"Intruder alert email sent to {target_email} for Incident #{incident_id}"
        )
        return {
            "status": "sent",
            "message": f"Alert successfully dispatched to {target_email}",
            "recipient": target_email
        }

    except Exception as e:
        error_msg = f"Failed to send email alert: {str(e)}"
        print(f"❌ {error_msg}")
        if incident_id:
            database.update_intruder_email_status(incident_id, status=-1, recipient=target_email)
        database.log_audit(
            event_type="EMAIL_ALERT_FAILED",
            status="WARNING",
            details=error_msg
        )
        return {
            "status": "failed",
            "message": error_msg,
            "recipient": target_email
        }

def send_test_email(recipient: str) -> Dict[str, Any]:
    """
    Sends a test verification email to confirm SMTP settings.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    dummy_path = Path(__file__).resolve().parent / "static" / "favicon.png"
    return send_intruder_email_alert(
        photo_path=dummy_path,
        timestamp=now_str,
        reason="SYSTEM_TEST: Verification of AegisVault Email Alert Engine",
        threat_level="LOW (TEST)",
        incident_id=0,
        recipient=recipient
    )
