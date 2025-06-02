import os
import csv
import os # os is used in __main__
import csv # csv is used in __main__
import json
from typing import List, Dict, Type
# from pydantic import BaseModel # BaseModel not directly used, SQLModel inherits from it.
from sqlmodel import SQLModel, Session, select # Added select here, Session is used. SQLModel for type hints.
import logging

from uploader import read_csv_file
from mapping import load_mapping_profile, apply_mapping
from database import create_db_and_tables # get_session is not directly used in this file's functions
                                          # but used in __main__. For clarity, keep if __main__ is kept.
                                          # For now, assuming __main__ will be simplified or removed later.
                                          # Let's remove get_session from here if not used by main functions.

# Import the specific SQLModel table models from models.py that engine will interact with.
from models import Customer, Supplier, Account as GeneralLedgerAccountSQLModel, Product, User as UserModel

# Imports for get_full_audit_data_for_xml and __main__ example
from models import (Header, MasterFiles, GeneralLedgerAccounts, GeneralLedgerEntries, AuditFile,
                    AddressStructure, SAFPTDateSpan, TaxAccountingBasisEnum, CurrencyPT, ProductIDType,
                    TaxonomyReferenceEnum)
from core.config import DEMO_USER_USERNAME
from datetime import date as py_date
from decimal import Decimal


logger = logging.getLogger(__name__)

# Flag to ensure DB and tables are created only once per application run
# In a more complex app, this might be handled by an app lifecycle event (e.g., FastAPI startup)
_db_initialized = False

def ensure_db_initialized():
    global _db_initialized
    if not _db_initialized:
        logger.info("Database not initialized. Calling create_db_and_tables().")
        create_db_and_tables() # This needs all SQLModel table classes to be imported/defined
        _db_initialized = True
    else:
        logger.debug("Database already initialized.")


def process_and_store_file(
    csv_file_path: str,
    mapping_profile_path: str,
    available_saft_models: Dict[str, Type[SQLModel]] # Expecting SQLModel types for DB operations
) -> List[SQLModel]:
    """
    Orchestrates reading a CSV, applying mapping, transforming data into SQLModel instances,
    and storing them in the database. 
    Note: In the current demo-only application, this function is not directly used by the UI flow 
    but could be used for administrative data loading if adapted (e.g. to assign owner_id).

    Args:
        csv_file_path: Path to the source CSV file.
        mapping_profile_path: Path to the JSON mapping profile.
        available_saft_models: A dictionary mapping SAF-T model names
                               (e.g., "Customer") to their SQLModel classes.

    Returns:
        A list of populated and stored SQLModel instances.
        Returns an empty list if any critical step fails.
    """
    ensure_db_initialized() 
    logger.info(f"Starting CSV processing and storing: {csv_file_path} with mapping: {mapping_profile_path}")

    processed_models: List[SQLModel] = []

    try:
        logger.info(f"Reading CSV file: {csv_file_path}")
        data_rows = read_csv_file(csv_file_path)
        if not data_rows:
            logger.warning(f"No data found in CSV: {csv_file_path}. Returning empty list.")
            return []
        logger.info(f"Read {len(data_rows)} rows from CSV.")

        logger.info(f"Loading mapping profile: {mapping_profile_path}")
        mapping_profile = load_mapping_profile(mapping_profile_path)
        logger.info(f"Loaded mapping profile: '{mapping_profile.profile_name}' for model '{mapping_profile.target_model}'.")

        # Check if the target model from profile is one we intend to store
        target_model_name = mapping_profile.target_model
        TargetModelClass = available_saft_models.get(target_model_name)

        if not TargetModelClass:
            logger.error(f"Target model '{target_model_name}' from profile not found in provided SQLModel registry. Skipping processing.")
            return []
        
        # Check if it's a SQLModel
        if not issubclass(TargetModelClass, SQLModel):
            logger.error(f"Target model '{target_model_name}' is not a SQLModel. Cannot process for DB storage.")
            return []

        logger.info(f"Applying mapping for target model: {target_model_name}")
        transformed_models = apply_mapping(data_rows, mapping_profile, available_saft_models)
        logger.info(f"Transformed data into {len(transformed_models)} '{target_model_name}' model instances.")

        if not transformed_models:
            logger.warning("No models were successfully transformed. Nothing to store.")
            return []

        logger.info(f"Attempting to store {len(transformed_models)} instances of '{target_model_name}' into the database.")
        stored_count = 0
        # Need to import get_session from database to use it here.
        from database import get_session as get_db_session_for_engine # Alias to avoid conflict if already imported
        with get_db_session_for_engine() as session:
            for model_instance in transformed_models:
                if isinstance(model_instance, SQLModel): 
                    try:
                        session.add(model_instance)
                        stored_count += 1
                    except Exception as db_err:
                        logger.error(f"Error adding instance {model_instance} to session: {db_err}", exc_info=True)
                        session.rollback() 
                        continue 
                else:
                    logger.warning(f"Instance {type(model_instance)} is not a SQLModel, cannot store in DB. Skipping.")
            
            if stored_count > 0:
                try:
                    session.commit() 
                    logger.info(f"Successfully committed {stored_count} instances of '{target_model_name}' to the database.")
                    processed_models.extend(transformed_models) 
                except Exception as commit_err:
                    logger.error(f"Error committing session to database: {commit_err}", exc_info=True)
                    session.rollback()
                    return [] 
            else:
                logger.info("No new instances were added to the session for commit.")
                processed_models.extend(transformed_models)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}", exc_info=True)
        return []
    except ValueError as e: 
        logger.error(f"Configuration or data error: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error in process_and_store_file: {e}", exc_info=True)
        return []
    
    # Return models that were successfully transformed.
    # If only successfully stored models are desired, adjust logic above.
    return processed_models


if __name__ == '__main__':
    print("Attempting example usage of engine.py with database operations...")

    # This registry should map to the actual SQLModel classes from models.py
    saft_sqlmodel_registry = {
        "Customer": Customer,
        "Supplier": Supplier,
        "GeneralLedgerAccount": GeneralLedgerAccountSQLModel, # Note: This is models.Account, aliased here
        "Product": Product,
    }
    
    # --- Imports for the new function and its example ---
    from models import AuditFile # The top-level Pydantic model for the entire SAF-T file
    from xml_generator import generate_saft_xml
    from xsd_validator import validate_saft_xml
    # For example construction & get_full_audit_data_for_xml:
    from models import (Header, MasterFiles, GeneralLedgerAccounts, GeneralLedgerEntries, SAFPTDateSpan, AddressStructure,
                        AuditFileVersion, CompanyIDType, SAFPTPortugueseVatNumber, TaxAccountingBasisEnum,
                        CurrencyPT, ProductIDType, TaxonomyReferenceEnum, User as UserModel) # Added GeneralLedgerAccounts, TaxonomyReferenceEnum, User
    from core.config import DEMO_USER_USERNAME # For demo user specific header
    from sqlmodel import select # Needed for queries
    from datetime import date as py_date
    from decimal import Decimal


    current_dir = os.path.dirname(__file__) if '__file__' in locals() else os.getcwd()
    
    # Use a temporary DB for the example run to avoid cluttering saft_data.db
    # or ensure saft_data.db is understood to be modified by this example.
    # For this example, let create_db_and_tables use its default DATABASE_URL ("sqlite:///saft_data.db")
    # The ensure_db_initialized() will handle creation.

    sample_csv_path = os.path.join(current_dir, "sample_data", "sample_customers.csv")
    sample_mapping_path = os.path.join(current_dir, "sample_data", "sample_mapping_profile.json")

    # Ensure sample files exist for the example
    if not os.path.exists("sample_data"):
        os.makedirs("sample_data")
    if not os.path.exists(sample_csv_path):
        with open(sample_csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Client ID","Company Name","Billing Address","City","Postal Code","Country","Tax ID", "Account Ref", "Self Bill"])
            writer.writerow(["C001EX","Example Corp","1 Example St","Exemplaria","EX123","PT","PTNIF01EX", "ACCEX01", "1"])
            writer.writerow(["C002EX","Another Corp","2 Example St","Exemplaria","EX456","US","USNIF02EX", "Desconhecido", "0"])
        print(f"Created dummy {sample_csv_path}")
    if not os.path.exists(sample_mapping_path):
         with open(sample_mapping_path, "w") as f:
            json.dump({
                "profile_name": "Example Customer Mapping for DB",
                "target_model": "Customer", # Must match a key in saft_sqlmodel_registry
                "mappings": {
                    "Client ID": "CustomerID",
                    "Company Name": "CompanyName",
                    "Billing Address": "BillingAddress.AddressDetail", # Assuming Customer.BillingAddress is JSON
                    "City": "BillingAddress.City",
                    "Postal Code": "BillingAddress.PostalCode",
                    "Country": "BillingAddress.Country",
                    "Tax ID": "CustomerTaxID",
                    "Account Ref": "AccountID",
                    "Self Bill": "SelfBillingIndicator"
                }
            }, f)
         print(f"Created dummy {sample_mapping_path}")

    print(f"Using CSV: {sample_csv_path}")
    print(f"Using Mapping: {sample_mapping_path}")

    # Call the processing function
    # The available_saft_models dict should contain the actual SQLModel classes
    # results = process_and_store_file(sample_csv_path, sample_mapping_path, saft_sqlmodel_registry) # Comment out for now to focus on XML part
    # if results:
    #     print(f"\nSuccessfully processed and attempted to store {len(results)} model instances:")
    #     for instance_ G in results:
    #         print(instance_G.model_dump_json(indent=2))
    #         if hasattr(instance_G, 'id') and instance_G.id is not None:
    #             print(f"  Instance ID from DB: {instance_G.id}")
    #         else:
    #             print("  Instance ID not populated (check logs if storage was expected).")
    # else:
    #     print("\nProcessing resulted in no instances or storage failed. Check logs.")
        
    # print("\nEngine example usage with database finished.")
    # Note: The saft_data.db file would be created/updated in the current directory.


# --- New function to assemble AuditFile from DB data ---
def get_full_audit_data_for_xml(db_session: Session, current_user: UserModel) -> AuditFile:
    """
    Queries relevant data from the database, filtered by the current user where applicable,
    and assembles the full AuditFile Pydantic model.
    """
    logger.info(f"Assembling full AuditFile data from database for user: {current_user.username} (ID: {current_user.id})")

    # 1. Construct Header
    company_name_for_header = f"{current_user.username}'s Company"
    company_id_for_header = "999999990" 
    tax_reg_number_for_header = 999999990 
    
    if current_user.username == DEMO_USER_USERNAME:
        company_name_for_header = "Demo Company SA (SAF-T View)"
        company_id_for_header = "DEMO00001" 
        tax_reg_number_for_header = 999000001

    header = Header(
        AuditFileVersion="1.04_01", CompanyID=company_id_for_header, TaxRegistrationNumber=tax_reg_number_for_header, 
        TaxAccountingBasis=TaxAccountingBasisEnum.F, CompanyName=company_name_for_header,
        CompanyAddress=AddressStructure(AddressDetail="Rua Ficticia, 123", City="User City", PostalCode="9999-000", Country="PT"),
        FiscalYear=py_date.today().year, StartDate=SAFPTDateSpan(py_date.today().year, 1, 1), EndDate=SAFPTDateSpan(py_date.today().year, 12, 31),
        CurrencyCode=CurrencyPT.EUR, DateCreated=SAFPTDateSpan.today(), TaxEntity="Global", 
        ProductCompanyTaxID="500000000", SoftwareCertificateNumber=1234, ProductID="MySAFTGenerator/1.1", ProductVersion="1.1",
        HeaderComment=f"SAF-T PT generated for {current_user.username}",
        Telephone="+351912345678", Fax="+351210000000", Email=current_user.email if current_user.email else f"{current_user.username}@example.com",
        Website="www.usercompany.example.com"
    )

    # 2. Fetch MasterFiles data - Filtered by owner_id where applicable
    customers_stmt = select(Customer).where(Customer.owner_id == current_user.id)
    customers = db_session.exec(customers_stmt).all()
    
    # Supplier, Product, GeneralLedgerAccountSQLModel do NOT have owner_id. Fetch all.
    suppliers = db_session.exec(select(Supplier)).all()
    products = db_session.exec(select(Product)).all()
    gl_accounts_db = db_session.exec(select(GeneralLedgerAccountSQLModel)).all()
    
    general_ledger_accounts_model = GeneralLedgerAccounts(
        TaxonomyReference=TaxonomyReferenceEnum.S, Account=gl_accounts_db
    ) if gl_accounts_db else None

    master_files = MasterFiles(
        Customer=customers if customers else None, Supplier=suppliers if suppliers else None,
        Product=products if products else None, GeneralLedgerAccounts=general_ledger_accounts_model
    )

    # 3. Construct GeneralLedgerEntries (empty for now)
    general_ledger_entries = GeneralLedgerEntries(
        NumberOfEntries=0, TotalDebit=Decimal("0.00"), TotalCredit=Decimal("0.00"), Journal=[]
    )
    
    audit_file_instance = AuditFile(
        Header=header, MasterFiles=master_files, GeneralLedgerEntries=general_ledger_entries
    )
    
    logger.info("AuditFile data assembled successfully.")
    return audit_file_instance


# --- Function for XML generation and validation ---
