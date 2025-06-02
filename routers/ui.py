import os
from pathlib import Path
# from typing import List # List is not used

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select # Added select

import engine 
import models # For models.User, models.Customer, models.AuditFile
from database import get_session 
from core import dependencies 
from core.config import DEMO_USER_USERNAME # For setting context

# --- Configuration ---
router = APIRouter(
    prefix="/ui",
    tags=["UI"],
)

# Templates directory setup
# Assumes templates are in a 'templates' folder at the same level as this 'routers' folder's parent
# Or if routers/ is at root, then just 'templates'
# Path(__file__).resolve().parent.parent refers to the directory containing the 'routers' folder
# BASE_PATH = Path(__file__).resolve().parent.parent 
# TEMPLATES_DIR = BASE_PATH / "templates"
# For a flat structure, it might be:
TEMPLATES_DIR = Path(".") / "templates" # if main.py is in root and templates is in root.
# Let's assume a structure where main.py is at root, and templates/ is also at root.
# If this ui.py is in routers/ then relative path to root is ..
# Path(__file__).resolve() -> /path/to/project/routers/ui.py
# Path(__file__).resolve().parent -> /path/to/project/routers
# Path(__file__).resolve().parent.parent -> /path/to/project
# So, TEMPLATES_DIR should be Path(__file__).resolve().parent.parent / "templates"
# For simplicity with the tool, let's assume templates are findable from current dir or relative.
# The FastAPI app instantiation in main.py will be the source of truth for base path.
# We'll define templates relative to a base path that should be the project root.

# This is a common way to set up templates if main.py is in the project root
# and 'templates' is a subdirectory of the project root.
templates_path = Path(__file__).parent.parent / "templates"
if not templates_path.exists(): # Fallback for flat structure
    templates_path = Path("templates")
templates = Jinja2Templates(directory=str(templates_path))


# Path to XSD file - needed for XML validation
# Assuming XSD is in the root of the project.
XSD_FILE_PATH = Path(__file__).parent.parent / "SAFTPT1_04_01.xsd"
if not XSD_FILE_PATH.exists(): # Fallback for flat structure
    XSD_FILE_PATH = Path("SAFTPT1_04_01.xsd")


# --- Helper to check XSD existence ---
def get_xsd_path_or_error_response(request: Request) -> str:
    if not XSD_FILE_PATH.exists():
        error_msg = f"Critical Error: SAF-T XSD file not found at expected location: {XSD_FILE_PATH.resolve()}"
        # Render an error page immediately if XSD is missing, as generation is not possible.
        # This is a server configuration issue.
        # In a real app, you might raise an HTTPException that's handled globally.
        # For now, directly returning an HTML response for simplicity in this context.
        # However, FastAPI endpoints expect to return a Response, not call another handler.
        # So, it's better to raise HTTPException. This will be caught by FastAPI.
        raise HTTPException(
            status_code=500, 
            detail=error_msg 
            # detail can be passed to a custom exception handler to render an HTML page
        )
    return str(XSD_FILE_PATH)


# --- UI Endpoints ---

@router.get("/view/customers", response_class=HTMLResponse)
async def view_customers(
    request: Request, 
    db: Session = Depends(get_session),
    # Changed dependency: always use demo_user_context now
    demo_user_context: models.User = Depends(dependencies.get_demo_user_context) 
):
    """
    Displays a list of customers from the database, always for the demo user.
    The user context is provided by the `get_demo_user_context` dependency.
    """
    # All data operations are now in the context of the demo user.
    customers_query = select(models.Customer).where(models.Customer.owner_id == demo_user_context.id)
    customers = db.exec(customers_query).all()
    
    return templates.TemplateResponse(
        "customers_view.html",
        {
            "request": request, 
            "customers": customers, 
            "current_username": demo_user_context.username, 
            "is_demo_mode": True 
        }
    )

@router.get("/actions/generate-saft") 
async def generate_saft_action(
    request: Request, 
    db: Session = Depends(get_session),
    demo_user_context: models.User = Depends(dependencies.get_demo_user_context) 
):
    """
    Generates the SAF-T XML file (always for the demo user), validates it, 
    and provides it for download or shows an error page if validation fails.
    The user context is provided by the `get_demo_user_context` dependency.
    """
    xsd_path_str = get_xsd_path_or_error_response(request) 

    try:
        audit_file_data: models.AuditFile = engine.get_full_audit_data_for_xml(
            db_session=db, 
            current_user=demo_user_context 
        )
        xml_string, validation_errors = engine.generate_and_validate_saft_file(
            audit_file_data=audit_file_data,
            xsd_path=xsd_path_str
        )

        if xml_string and not validation_errors:
            # 3. If valid, stream the XML file for download
            return StreamingResponse(
                iter([xml_string.encode("utf-8")]), # XML string needs to be encoded to bytes for streaming
                media_type="application/xml",
                headers={"Content-Disposition": "attachment; filename=saft_pt_report.xml"}
            )
        else:
            # 4. If validation fails, show an error page with the validation messages
            return templates.TemplateResponse(
                "error.html",
                {"request": request, "errors": validation_errors if validation_errors else ["Unknown validation error."]}
            )

    except HTTPException:
        raise # Re-raise HTTPException from get_xsd_path_or_error_response
    except Exception as e:
        # Catch any other unexpected errors during the process
        # Log the exception e here with logging module if available
        return templates.TemplateResponse(
            "error.html",
            {"request": request, "errors": [f"An unexpected server error occurred: {str(e)}"]}
        )
