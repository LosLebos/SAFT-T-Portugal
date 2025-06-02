# --- Demo User Configuration ---
DEMO_USER_USERNAME = "demo_user"
# IMPORTANT: This is a default password for a demo account.
# It will be hashed when the demo user is created.
# For any real deployment, ensure this is handled securely if used, or disable demo mode.
DEMO_USER_PASSWORD = "Dem0UserP@sswOrd!" # Reasonably complex for a default

# --- Other application level configurations can go here ---
# For example:
# PROJECT_NAME = "SAF-T Tools"
# API_V1_STR = "/api/v1"

# XSD File Path (centralizing it here)
# In a real app, this might come from an environment variable or be more dynamic.
import os
from pathlib import Path

# Try to determine project root to locate XSD reliably
# This assumes config.py is in 'core' directory, one level down from project root.
PROJECT_ROOT_FROM_CONFIG = Path(__file__).resolve().parent.parent 
DEFAULT_XSD_FILE_PATH = PROJECT_ROOT_FROM_CONFIG / "SAFTPT1_04_01.xsd"

# Allow override via environment variable if needed
SAFT_XSD_PATH = os.getenv("SAFT_XSD_PATH", str(DEFAULT_XSD_FILE_PATH))

if __name__ == '__main__':
    print("--- Configuration Settings ---")
    print(f"Demo User Username: {DEMO_USER_USERNAME}")
    print(f"Demo User Password: (not shown)")
    print(f"SAF-T XSD Path (resolved): {SAFT_XSD_PATH}")
    if not Path(SAFT_XSD_PATH).exists():
        print(f"WARNING: XSD file not found at the configured path: {SAFT_XSD_PATH}")
    print("--- End of Configuration ---")
