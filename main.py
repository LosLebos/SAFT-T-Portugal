from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse # For potential global error handling
from pathlib import Path
import logging

# Assuming database.py and routers modules are accessible
# Adjust if project structure is different (e.g. app.database, app.routers.ui)
from database import create_db_and_tables, get_session # Use get_session for startup data population
from routers import ui as ui_router
# No longer importing auth_router as it's deleted
from core import demo_data # For populating demo data

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Application Setup ---
app = FastAPI(title="SAF-T PT Tools", version="0.1.0")

# --- Determine Base Path ---
# This helps in locating static/templates relative to the main.py file's location.
# Path(__file__).resolve() gives the full path to main.py
# .parent gives the directory containing main.py
BASE_DIR = Path(__file__).resolve().parent

# --- Static Files ---
# Mount a static directory (even if not heavily used yet, it's good practice)
# The directory "static" should be at the same level as main.py
static_files_path = BASE_DIR / "static"
if not static_files_path.exists():
    static_files_path.mkdir(parents=True, exist_ok=True) # Create if it doesn't exist
app.mount("/static", StaticFiles(directory=static_files_path), name="static")


# --- Templates ---
# Although Jinja2Templates is initialized in ui.py, if you had global error pages
# or other direct template uses in main.py, you might init one here too.
# For now, ui.py handles its own template needs.


# --- Event Handlers (e.g., Startup) ---
@app.on_event("startup")
async def startup_event():
    """
    Actions to perform on application startup.
    - Create database and tables.
    """
    logger.info("Application startup: Initializing database...")
    try:
        create_db_and_tables()
        logger.info("Database and tables checked/created successfully.")
        
        # Populate demo data after tables are created
        logger.info("Attempting to populate demo data...")
        # Need a DB session for demo data population
        # FastAPI's Depends cannot be used directly in startup events.
        # So, we create a session manually for this startup task.
        # This is a common pattern for one-off startup tasks.
        
        # The get_session() from database.py is a generator.
        # We need to manually iterate it to get a session.
        session_generator = get_session()
        db_session_for_startup = next(session_generator)
        try:
            demo_user = demo_data.create_demo_user(db_session_for_startup)
            if demo_user and demo_user.is_active: # Ensure demo user is valid and active
                demo_data.populate_demo_data(db_session_for_startup, demo_user)
            logger.info("Demo data population check complete.")
        except Exception as demo_e:
            logger.error(f"Error during demo data population: {demo_e}", exc_info=True)
            db_session_for_startup.rollback() # Rollback on error during demo data population
        finally:
            # Ensure the session is closed.
            # For a generator session, sending None or calling close() on generator might be needed
            # or simply relying on the 'with Session(engine) as session:' context manager style in get_session.
            # If get_session() is `with Session(engine) as session: yield session`,
            # then `next()` gets the session, and the `finally` block of the generator handles closure
            # after this startup event function finishes or if an error occurs within the try using the session.
            # Let's assume get_session's finally block handles closure.
             pass # db_session_for_startup.close() might be needed if get_session doesn't auto-close on generator exit
             
    except Exception as e:
        logger.error(f"Error during database initialization or demo data population: {e}", exc_info=True)
        # Depending on severity, you might want to prevent app startup or handle differently.

# --- Routers ---
app.include_router(ui_router.router) 
app.include_router(auth_router.router) # Include the Authentication router

# --- Root Endpoint (Optional) ---
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    """
    A simple root endpoint that redirects to the customer view or shows a welcome page.
    """
    # For simplicity, redirecting or showing a link to the main UI view.
    # Using Jinja2Templates directly in main.py for this simple page:
    # Ensure 'templates' path is correctly defined if used here.
    # For now, a simple HTML string response.
    # templates_main = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    # return templates_main.TemplateResponse("welcome.html", {"request": request})
    
    # Or just a simple HTML response:
    html_content = """
    <html>
        <head>
            <title>SAF-T Tools Welcome</title>
            <style> body { font-family: Arial, sans-serif; text-align: center; margin-top: 50px; } </style>
        </head>
        <body>
            <h1>Welcome to SAF-T Tools</h1>
            <p>This application helps in processing and generating SAF-T (Standard Audit File for Tax) reports.</p>
            <p><a href="/ui/view/customers">View Customers and Generate SAF-T Report</a></p>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# --- Uvicorn Runner (for local development) ---
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server for local development...")
    # Make sure uvicorn can find the 'app' instance in this 'main.py' file.
    # Format is "filename:fastapi_app_instance_name"
    # If this file is main.py and instance is app, it's "main:app"
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
    # reload=True is great for development, watches for file changes.
```
