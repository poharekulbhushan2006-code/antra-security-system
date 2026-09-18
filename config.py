import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Security & Verification
FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.55"))
VAULT_AUTO_LOCK_SECONDS = int(os.getenv("VAULT_AUTO_LOCK_SECONDS", "10"))
INTRUDER_ALERT_COOLDOWN_SECONDS = int(os.getenv("INTRUDER_ALERT_COOLDOWN_SECONDS", "6"))
MAX_FAILED_PIN_ATTEMPTS = int(os.getenv("MAX_FAILED_PIN_ATTEMPTS", "3"))

# Storage Paths
DATABASE_PATH = BASE_DIR / "data" / "security_vault.db"
EVIDENCE_DIR = BASE_DIR / "evidence" / "intruders"
USER_PHOTOS_DIR = BASE_DIR / "evidence" / "users"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
USER_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)

# Email / Alert Notification Settings
ADMIN_ALERT_EMAIL = os.getenv("ADMIN_ALERT_EMAIL", "security-officer@antrasecurity.local")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER or "alerts@antrasecurity.local"
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# Bank & Terminal Metadata
BANK_NAME = os.getenv("BANK_NAME", "ANTRA SECURITY SYSTEM")
TERMINAL_ID = os.getenv("TERMINAL_ID", "VAULT AIR-LOCK // TERMINAL-01")
