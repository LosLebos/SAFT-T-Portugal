from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates # Not used directly in main.py anymore
from fastapi.responses import HTMLResponse
from pathlib import Path
import logging

from database import create_db_and_tables, get_session 
from routers import ui as ui_router
# auth_router was removed.
from core import demo_data 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(
    title="SAF-T PT Tools (Demo Mode)", 
    version="0.1.0",
    description="Application for processing and generating SAF-T (Standard Audit File for Tax) reports. Currently operating in demo mode."
)

# --- Determine Base Path ---
BASE_DIR = Path(__file__).resolve().parent

# --- Static Files ---
static_files_path = BASE_DIR / "static"
if not static_files_path.exists():
    static_files_path.mkdir(parents=True, exist_ok=True) 
app.mount("/static", StaticFiles(directory=static_files_path), name="static")

# --- Templates ---
# Handled by ui.py's Jinja2Templates instance.

# --- Event Handlers (e.g., Startup) ---
@app.on_event("startup")
async def startup_event():
    """
    Application startup actions:
    1. Create database tables (idempotent).
    2. Initialize and populate demo user and their associated data (idempotent).
    """
    logger.info("Application startup: Initializing database...")
    try:
        create_db_and_tables()
        logger.info("Database and tables checked/created successfully.")
        
        logger.info("Attempting to set up demo environment...")
        # Manually manage session for startup task
        session_generator = get_session()
        db_session_for_startup = next(session_generator)
        try:
            demo_user = demo_data.create_demo_user(db_session_for_startup)
            if demo_user and demo_user.is_active: 
                demo_data.populate_demo_data(db_session_for_startup, demo_user)
            logger.info("Demo environment setup check complete.")
        except Exception as demo_e:
            logger.error(f"Error during demo data setup: {demo_e}", exc_info=True)
            # db_session_for_startup.rollback() # Rollback if demo_data functions don't handle their own
        finally:
            # Assuming get_session() and its 'with Session...' pattern handles closure.
            pass 
             
    except Exception as e:
        logger.error(f"Critical error during application startup (database/demo data): {e}", exc_info=True)

# --- Routers ---
app.include_router(ui_router.router) 
# app.include_router(auth_router.router) # This line is now correctly removed.
 
# --- Root Endpoint (Optional) ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    """
    Root endpoint providing a welcome message for the demo application.
    """
    html_content = """
    <html>
        <head>
            <title>SAF-T Tools Welcome (Demo Mode)</title>
            <style> body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; } </style>
        </head>
        <body>
            <h1>Welcome to SAF-T Tools (Demo Mode)</h1>
            <p>This application assists with SAF-T (Standard Audit File for Tax) report generation.</p>
            <p>You are currently interacting with the application using pre-populated sample data.</p>
            <p><a href="/ui/view/customers">View Demo Customers and Generate SAF-T Report</a></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development (Demo Mode)...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```
