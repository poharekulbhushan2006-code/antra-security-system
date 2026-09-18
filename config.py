import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Security & Verification
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))
VAULT_AUTO_LOCK_SECONDS = int(os.getenv("VAULT_AUTO_LOCK_SECONDS", "10"))
INTRUDER_ALERT_COOLDOWN_SECONDS = int(os.getenv("INTRUDER_ALERT_COOLDOWN_SECONDS", "6"))
MAX_FAILED_PIN_ATTEMPTS = int(os.getenv("MAX_FAILED_PIN_ATTEMPTS", "3"))

# Detect serverless environment (Vercel / AWS Lambda)
IS_SERVERLESS = bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME") or not os.access(str(BASE_DIR), os.W_OK))

if IS_SERVERLESS:
    TMP_DIR = Path("/tmp")
    DATABASE_PATH = TMP_DIR / "security_vault.db"
    EVIDENCE_DIR = TMP_DIR / "evidence" / "intruders"
    USER_PHOTOS_DIR = TMP_DIR / "evidence" / "users"

    # Copy bundled read-only database to writable /tmp so Kulbhushan's profile is accessible and writable
    SEED_DB = BASE_DIR / "data" / "security_vault.db"
    if SEED_DB.exists() and not DATABASE_PATH.exists():
        try:
            shutil.copy2(SEED_DB, DATABASE_PATH)
            print("[INFO] Copied bundled database to /tmp/security_vault.db")
        except Exception as e:
            print(f"[WARN] Failed to copy seed db: {e}")

    # Copy existing user photos to /tmp
    SEED_USER_PHOTOS = BASE_DIR / "evidence" / "users"
    if SEED_USER_PHOTOS.exists() and not USER_PHOTOS_DIR.exists():
        try:
            shutil.copytree(SEED_USER_PHOTOS, USER_PHOTOS_DIR, dirs_exist_ok=True)
        except Exception:
            pass
else:
    DATABASE_PATH = BASE_DIR / "data" / "security_vault.db"
    EVIDENCE_DIR = BASE_DIR / "evidence" / "intruders"
    USER_PHOTOS_DIR = BASE_DIR / "evidence" / "users"

try:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    USER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

# Email / Alert Notification Settings
ADMIN_ALERT_EMAIL = os.getenv("ADMIN_ALERT_EMAIL", "poharekulbhushan2006@gmail.com")
ADMIN_PHONE_NUMBER = os.getenv("ADMIN_PHONE_NUMBER", "9834481366")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER or "alerts@antrasecurity.local"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Bank & Terminal Metadata
BANK_NAME = os.getenv("BANK_NAME", "ANTRA SECURITY SYSTEM")
TERMINAL_ID = os.getenv("TERMINAL_ID", "VAULT AIR-LOCK // TERMINAL-01")
