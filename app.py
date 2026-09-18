import os
import re
import time
import uuid
import base64
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import (
    BASE_DIR,
    EVIDENCE_DIR,
    USER_PHOTOS_DIR,
    FACE_MATCH_THRESHOLD,
    VAULT_AUTO_LOCK_SECONDS,
    INTRUDER_ALERT_COOLDOWN_SECONDS,
    MAX_FAILED_PIN_ATTEMPTS,
    ADMIN_ALERT_EMAIL,
    BANK_NAME,
    TERMINAL_ID,
)
import database
import security
import email_service

app = FastAPI(title="Antra Security System", version="2.0.0")

# Mount static and evidence folders
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.mount("/evidence", StaticFiles(directory=str(BASE_DIR / "evidence")), name="evidence")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# State tracking for cooldowns & failed PIN attempts
last_intruder_alert_time = 0.0
user_failed_attempts = {}

# --- Pydantic Request Models ---

class FaceVerifyRequest(BaseModel):
    descriptor: List[float]

class VaultUnlockRequest(BaseModel):
    user_id: int
    pin: str
    snapshot_base64: Optional[str] = None

class IntruderReportRequest(BaseModel):
    image_base64: str
    reason: str = "Unregistered face detected at terminal"
    score: float = 0.0

class UserRegisterRequest(BaseModel):
    name: str
    employee_id: str
    role: str
    pin: str
    descriptor: List[float]
    image_base64: Optional[str] = None

class SettingsUpdateRequest(BaseModel):
    admin_alert_email: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    face_threshold: Optional[float] = None
    auto_lock_seconds: Optional[int] = None

class TestEmailRequest(BaseModel):
    recipient: Optional[str] = None

# --- Helper Functions ---

def save_base64_image(base64_str: str, target_path: Path) -> Path:
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if "," in base64_str:
            base64_str = base64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_str)
        with open(target_path, "wb") as f:
            f.write(img_bytes)
    except Exception as e:
        print(f"[WARN] Failed to write image to {target_path}: {e}")
    return target_path

# --- Web Page Views ---

@app.get("/", response_class=HTMLResponse)
async def kiosk_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "bank_name": BANK_NAME,
            "terminal_id": TERMINAL_ID,
            "auto_lock_seconds": database.get_setting("auto_lock_seconds") or VAULT_AUTO_LOCK_SECONDS
        }
    )

@app.get("/admin", response_class=HTMLResponse)
async def admin_view(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "bank_name": BANK_NAME,
            "terminal_id": TERMINAL_ID,
            "admin_email": database.get_setting("admin_alert_email") or ADMIN_ALERT_EMAIL
        }
    )

# --- Biometric & Access Control API ---

@app.post("/api/verify-face")
async def verify_face(payload: FaceVerifyRequest):
    """
    Step 1 of 2FA: Matches client face descriptor against active personnel.
    """
    threshold_str = database.get_setting("face_threshold")
    threshold = float(threshold_str) if threshold_str else FACE_MATCH_THRESHOLD
    
    registered = database.get_all_users_with_descriptors()
    is_match, matched_user, distance = security.match_face_descriptor(
        payload.descriptor, registered, threshold
    )
    
    if is_match and matched_user:
        return {
            "matched": True,
            "user": {
                "id": matched_user["id"],
                "name": matched_user["name"],
                "employee_id": matched_user["employee_id"],
                "role": matched_user["role"],
                "photo_filename": matched_user["photo_filename"]
            },
            "distance": round(distance, 4),
            "threshold": threshold
        }
    else:
        return {
            "matched": False,
            "distance": round(distance, 4) if distance != 999.0 else None,
            "threshold": threshold
        }

@app.post("/api/unlock-vault")
async def unlock_vault(payload: VaultUnlockRequest, background_tasks: BackgroundTasks):
    """
    Step 2 of 2FA: Verifies secret PIN after face identification to unlock the vault.
    """
    try:
        user = database.get_user_by_id(payload.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = user["id"]
        current_failures = user_failed_attempts.get(user_id, 0)
        
        is_pin_valid = security.verify_pin(payload.pin, user["pin_hash"], user["pin_salt"])
        
        if is_pin_valid:
            # Reset failed attempts
            user_failed_attempts[user_id] = 0
            
            try:
                database.log_audit(
                    event_type="VAULT_UNLOCKED",
                    status="SUCCESS",
                    details=f"Authorized 2FA access granted to {user['name']} ({user['employee_id']})",
                    user_name=user["name"],
                    employee_id=user["employee_id"]
                )
            except Exception as e:
                print(f"[WARN] Audit write skipped: {e}")

            return {
                "success": True,
                "message": f"Security Clearance Granted. Welcome, {user['name']}.",
                "auto_lock_seconds": int(database.get_setting("auto_lock_seconds") or VAULT_AUTO_LOCK_SECONDS)
            }
        else:
            # Invalid PIN
            current_failures += 1
            user_failed_attempts[user_id] = current_failures
            
            try:
                database.log_audit(
                    event_type="ACCESS_DENIED_PIN",
                    status="WARNING",
                    details=f"Incorrect PIN entered for user {user['name']} ({user['employee_id']}). Attempt #{current_failures}",
                    user_name=user["name"],
                    employee_id=user["employee_id"]
                )
            except Exception as e:
                print(f"[WARN] Audit write skipped: {e}")
            
            # If repeated failures exceed limit, treat as potential impersonation / coercion
            if current_failures >= MAX_FAILED_PIN_ATTEMPTS:
                incident_photo = None
                if payload.snapshot_base64:
                    filename = f"pin_breach_{user['employee_id']}_{int(time.time())}.jpg"
                    filepath = EVIDENCE_DIR / filename
                    save_base64_image(payload.snapshot_base64, filepath)
                    incident_photo = filename
                    
                    log_id = database.log_intruder(
                        photo_filename=filename,
                        reason=f"Multiple failed PIN attempts for {user['name']} ({user['employee_id']}) - Potential Coercion/Compromise",
                        threat_level="CRITICAL"
                    )
                    
                    # Dispatch alert
                    background_tasks.add_task(
                        email_service.send_intruder_email_alert,
                        photo_path=filepath,
                        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        reason=f"Security Lockout: 3+ Failed PIN attempts for identity {user['name']}",
                        threat_level="CRITICAL",
                        incident_id=log_id
                    )
                
                return {
                    "success": False,
                    "lockout": True,
                    "message": f"SECURITY LOCKOUT: Excessive incorrect PIN entries. Intrusion alert triggered!"
                }
            
            return {
                "success": False,
                "lockout": False,
                "attempts_remaining": MAX_FAILED_PIN_ATTEMPTS - current_failures,
                "message": f"Invalid PIN. {MAX_FAILED_PIN_ATTEMPTS - current_failures} attempts remaining before security lockout."
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] unlock_vault exception: {e}")
        return {
            "success": False,
            "message": f"Security verification error: {str(e)}"
        }

@app.post("/api/report-intruder")
async def report_intruder(payload: IntruderReportRequest, background_tasks: BackgroundTasks):
    """
    Intruder Detection & Evidence Capture:
    Saves snapshot of unregistered person, logs incident, and triggers email dispatch with photo.
    """
    global last_intruder_alert_time
    now = time.time()
    
    # Rate limit intruder alert notifications to avoid flooding mailbox
    cooldown = int(database.get_setting("alert_cooldown_seconds") or INTRUDER_ALERT_COOLDOWN_SECONDS)
    is_throttled = (now - last_intruder_alert_time) < cooldown
    
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"intruder_{timestamp_str}_{uuid.uuid4().hex[:6]}.jpg"
    photo_path = EVIDENCE_DIR / filename
    
    try:
        save_base64_image(payload.image_base64, photo_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process image: {str(e)}")
    
    # Record in database
    log_id = database.log_intruder(
        photo_filename=filename,
        reason=payload.reason,
        score=payload.score,
        threat_level="CRITICAL"
    )
    
    database.log_audit(
        event_type="INTRUDER_CAPTURED",
        status="CRITICAL",
        details=f"Unregistered face intercepted and captured. Incident #{log_id} logged to evidence."
    )
    
    # Dispatch email if not throttled
    email_status = "queued"
    if not is_throttled:
        last_intruder_alert_time = now
        background_tasks.add_task(
            email_service.send_intruder_email_alert,
            photo_path=photo_path,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            reason=payload.reason,
            threat_level="CRITICAL",
            incident_id=log_id
        )
    else:
        email_status = "throttled_cooldown"
        database.update_intruder_email_status(log_id, status=3) # 3 = Throttled
    
    return {
        "success": True,
        "incident_id": log_id,
        "photo_filename": filename,
        "photo_url": f"/evidence/intruders/{filename}",
        "email_status": email_status,
        "timestamp": datetime.now().isoformat()
    }

# --- Management & Registration API ---

@app.post("/api/register-user")
async def register_user(payload: UserRegisterRequest):
    """
    Enrolls a new authorized employee / vault custodian with Face ID & PIN.
    """
    if not payload.descriptor or len(payload.descriptor) != 128:
        raise HTTPException(status_code=400, detail="Invalid biometric face descriptor. 128 float features required.")
    
    if len(payload.pin) < 3:
        raise HTTPException(status_code=400, detail="Password/PIN must be at least 3 characters.")
    
    # Check if employee ID already exists
    for u in database.get_all_users():
        if u["employee_id"].strip().upper() == payload.employee_id.strip().upper():
            raise HTTPException(status_code=400, detail=f"Employee ID '{payload.employee_id}' is already registered.")
            
    # Save face photograph if provided
    photo_filename = ""
    if payload.image_base64:
        photo_filename = f"user_{re.sub(r'[^a-zA-Z0-9]', '_', payload.employee_id)}_{int(time.time())}.jpg"
        save_base64_image(payload.image_base64, USER_PHOTOS_DIR / photo_filename)
        
    pin_hash, pin_salt = security.hash_pin(payload.pin)
    
    user_id = database.create_user(
        name=payload.name.strip(),
        employee_id=payload.employee_id.strip().upper(),
        role=payload.role.strip(),
        pin_hash=pin_hash,
        pin_salt=pin_salt,
        face_descriptor=payload.descriptor,
        photo_filename=photo_filename
    )
    
    database.log_audit(
        event_type="USER_ENROLLED",
        status="SUCCESS",
        details=f"New authorized personnel enrolled: {payload.name} ({payload.employee_id}) as {payload.role}",
        user_name=payload.name,
        employee_id=payload.employee_id
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "message": f"Personnel '{payload.name}' enrolled successfully with Biometric Face ID & PIN."
    }

@app.get("/api/users")
async def list_users():
    return {"users": database.get_all_users()}

@app.delete("/api/users/{user_id}")
async def revoke_user(user_id: int):
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = database.delete_user(user_id)
    if success:
        database.log_audit(
            event_type="USER_REVOKED",
            status="WARNING",
            details=f"Revoked credentials for {user['name']} ({user['employee_id']})",
            user_name=user["name"],
            employee_id=user["employee_id"]
        )
        return {"success": True, "message": "User access revoked."}
    raise HTTPException(status_code=500, detail="Failed to revoke user.")

@app.get("/api/intruders")
async def list_intruders():
    return {"intruders": database.get_all_intruders(50)}

@app.post("/api/intruders/{incident_id}/resolve")
async def resolve_intruder(incident_id: int):
    success = database.mark_intruder_resolved(incident_id)
    if success:
        database.log_audit(
            event_type="INTRUDER_ARCHIVED",
            status="SUCCESS",
            details=f"Incident #{incident_id} marked as resolved and archived by security officer."
        )
        return {"success": True, "message": "Incident marked as resolved."}
    raise HTTPException(status_code=404, detail="Incident not found.")

@app.get("/api/audit-logs")
async def list_audit_logs():
    return {"logs": database.get_audit_logs(100)}

@app.get("/api/settings")
async def get_settings():
    return {
        "admin_alert_email": database.get_setting("admin_alert_email") or ADMIN_ALERT_EMAIL,
        "smtp_host": database.get_setting("smtp_host") or os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": database.get_setting("smtp_port") or str(os.getenv("SMTP_PORT", "587")),
        "smtp_user": database.get_setting("smtp_user") or os.getenv("SMTP_USER", ""),
        "smtp_from": database.get_setting("smtp_from") or os.getenv("SMTP_FROM", ""),
        "face_threshold": float(database.get_setting("face_threshold") or FACE_MATCH_THRESHOLD),
        "auto_lock_seconds": int(database.get_setting("auto_lock_seconds") or VAULT_AUTO_LOCK_SECONDS),
        "alert_cooldown_seconds": int(database.get_setting("alert_cooldown_seconds") or INTRUDER_ALERT_COOLDOWN_SECONDS)
    }

@app.post("/api/settings")
async def update_settings(payload: SettingsUpdateRequest):
    if payload.admin_alert_email is not None:
        database.set_setting("admin_alert_email", payload.admin_alert_email.strip())
    if payload.smtp_host is not None:
        database.set_setting("smtp_host", payload.smtp_host.strip())
    if payload.smtp_port is not None:
        database.set_setting("smtp_port", str(payload.smtp_port).strip())
    if payload.smtp_user is not None:
        database.set_setting("smtp_user", payload.smtp_user.strip())
    if payload.smtp_password is not None and payload.smtp_password != "":
        database.set_setting("smtp_password", payload.smtp_password.strip())
    if payload.smtp_from is not None:
        database.set_setting("smtp_from", payload.smtp_from.strip())
    if payload.face_threshold is not None:
        database.set_setting("face_threshold", str(payload.face_threshold))
    if payload.auto_lock_seconds is not None:
        database.set_setting("auto_lock_seconds", str(payload.auto_lock_seconds))
        
    database.log_audit(
        event_type="SETTINGS_UPDATED",
        status="SUCCESS",
        details="System security and alert notification parameters updated."
    )
    return {"success": True, "message": "Settings updated successfully."}

@app.post("/api/test-email")
async def trigger_test_email(payload: TestEmailRequest):
    recipient = payload.recipient or database.get_setting("admin_alert_email") or ADMIN_ALERT_EMAIL
    result = email_service.send_test_email(recipient)
    return result
