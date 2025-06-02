from sqlmodel import Session, select
from typing import List
from decimal import Decimal
import logging

# Assuming models, crud.user_crud, core.security, core.config are accessible
# Adjust paths if needed (e.g. from .. import models)
import models
from crud import user_crud
from core.security import get_password_hash
from core.config import DEMO_USER_USERNAME, DEMO_USER_PASSWORD
# from schemas import user_schemas # For UserCreate schema -> This line is removed

logger = logging.getLogger(__name__)

def create_demo_user(db: Session) -> models.User:
    """
    Creates the demo user if it doesn't already exist.
    Returns the demo user (either existing or newly created).
    """
    logger.info(f"Attempting to find or create demo user: {DEMO_USER_USERNAME}")
    demo_user = user_crud.get_user_by_username(db, username=DEMO_USER_USERNAME)
    if not demo_user:
        logger.info(f"Demo user '{DEMO_USER_USERNAME}' not found, creating now.")
        # user_schemas.UserCreate is removed. Call user_crud.create_user with direct params.
        # The create_user function in user_crud now handles password hashing.
        demo_user = user_crud.create_user(
            db=db,
            username=DEMO_USER_USERNAME,
            password=DEMO_USER_PASSWORD, # Pass plain password here
            email=f"{DEMO_USER_USERNAME}@example.com"
            # is_active and is_superuser will use defaults from create_user
        )
        logger.info(f"Demo user '{DEMO_USER_USERNAME}' created successfully.")
    else:
        logger.info(f"Demo user '{DEMO_USER_USERNAME}' already exists.")
        if not demo_user.is_active:
            logger.warning(f"Demo user '{DEMO_USER_USERNAME}' exists but is INACTIVE. Activating now.")
            demo_user.is_active = True
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
    return demo_user

def populate_demo_data(db: Session, demo_user: models.User):
    """
    Populates the database with sample data owned by the demo user.
    Checks if data for this owner already exists to avoid duplication.
    """
    if not demo_user or not demo_user.id:
        logger.error("Cannot populate demo data: Invalid demo user provided.")
        return

    logger.info(f"Checking if demo data needs to be populated for user ID: {demo_user.id} ({demo_user.username})")

    # Check if customers for this owner already exist
    existing_customers_stmt = select(models.Customer).where(models.Customer.owner_id == demo_user.id)
    if db.exec(existing_customers_stmt).first():
        logger.info(f"Demo customers already exist for user '{demo_user.username}'. Skipping customer population.")
    else:
        logger.info(f"Populating demo customers for user '{demo_user.username}'...")
        demo_customers_data = [
            {"CustomerID": "DEMOCUST001", "CompanyName": "Gadgets & Gizmos Ltd (Demo)", "AccountID": "211DEMO01", "CustomerTaxID": "PT999000001", 
             "BillingAddress": {"AddressDetail": "1 Demo Street", "City": "Demoville", "PostalCode": "1000-001", "Country": "PT"}, "owner_id": demo_user.id},
            {"CustomerID": "DEMOCUST002", "CompanyName": "Innovative Solutions (Demo)", "AccountID": "211DEMO02", "CustomerTaxID": "PT999000002", 
             "BillingAddress": {"AddressDetail": "2 Creative Ave", "City": "Testburg", "PostalCode": "2000-002", "Country": "PT"}, "owner_id": demo_user.id},
        ]
        for cust_data in demo_customers_data:
            addr = models.CustomerAddressStructure(**cust_data.pop("BillingAddress"))
            db.add(models.Customer(**cust_data, BillingAddress=addr))
        logger.info(f"Added {len(demo_customers_data)} demo customers.")

    # Check if suppliers for this owner exist (assuming suppliers also had owner_id, but they don't currently)
    # For now, demo suppliers will be generic if not owned. If they were owned, similar logic as customers.
    # Let's assume for demo purposes, suppliers are global or we add some generic ones if none exist at all.
    if not db.exec(select(models.Supplier)).first(): # Add some global demo suppliers if table is empty
        logger.info(f"Populating global demo suppliers...")
        demo_suppliers_data = [
            {"SupplierID": "DEMOSUP001", "CompanyName": "Global Parts Co (Demo)", "AccountID": "221DEMOSUP01", "SupplierTaxID": "ESDEMO00001", 
             "BillingAddress": {"AddressDetail": "1 Supply Route", "City": "Madrid", "PostalCode": "28001", "Country": "ES"}},
            {"SupplierID": "DEMOSUP002", "CompanyName": "Material World (Demo)", "AccountID": "221DEMOSUP02", "SupplierTaxID": "FRDEMO00002", 
             "BillingAddress": {"AddressDetail": "10 Resource Blvd", "City": "Paris", "PostalCode": "75001", "Country": "FR"}},
        ]
        for sup_data in demo_suppliers_data:
            addr = models.AddressStructure(**sup_data.pop("BillingAddress"))
            db.add(models.Supplier(**sup_data, BillingAddress=addr))
        logger.info(f"Added {len(demo_suppliers_data)} global demo suppliers.")
    else:
        logger.info("Suppliers table is not empty. Skipping global demo supplier population.")


    # Check if products for this owner exist
    existing_products_stmt = select(models.Product).where(models.Product.owner_id == demo_user.id if hasattr(models.Product, 'owner_id') else True) # Product might not have owner_id
    # For now, Product doesn't have owner_id. Let's add generic demo products if table is empty.
    if not db.exec(select(models.Product)).first():
        logger.info(f"Populating global demo products...")
        demo_products_data = [
            {"ProductType": models.ProductTypeEnum.P, "ProductCode": "DEMOPROD001", "ProductDescription": "Standard Widget (Demo)", "ProductNumberCode": "SW001"},
            {"ProductType": models.ProductTypeEnum.S, "ProductCode": "DEMOSERV001", "ProductDescription": "Basic Service Package (Demo)", "ProductNumberCode": "BSP001"},
            {"ProductType": models.ProductTypeEnum.P, "ProductCode": "DEMOPROD002", "ProductDescription": "Advanced Gadget (Demo)", "ProductNumberCode": "AG002",
             "CustomsDetails": {"CNCode": ["99990000"], "UNNumber": ["0000"]}}
        ]
        for prod_data in demo_products_data:
            customs = models.CustomsDetails(**prod_data.pop("CustomsDetails")) if "CustomsDetails" in prod_data else None
            db.add(models.Product(**prod_data, CustomsDetails=customs))
        logger.info(f"Added {len(demo_products_data)} global demo products.")
    else:
         logger.info("Products table is not empty. Skipping global demo product population.")


    # Check if GL Accounts for this owner exist
    existing_gl_accounts_stmt = select(models.Account).where(models.Account.owner_id == demo_user.id if hasattr(models.Account, 'owner_id') else True) # Account might not have owner_id
    # Account (GeneralLedgerAccountSQLModel) doesn't have owner_id. Add generic demo accounts if table is empty.
    if not db.exec(select(models.Account)).first():
        logger.info(f"Populating global demo General Ledger Accounts...")
        demo_gl_accounts_data = [
            {"AccountID": "111001", "AccountDescription": "Caixa Sede (Demo)", "OpeningDebitBalance": Decimal("1000.00"), "OpeningCreditBalance": Decimal("0.00"), "ClosingDebitBalance": Decimal("0.00"), "ClosingCreditBalance": Decimal("0.00"), "GroupingCategory": models.GroupingCategoryEnum.GM, "TaxonomyCode": 211},
            {"AccountID": "211001", "AccountDescription": "Clientes C/C (Demo)", "OpeningDebitBalance": Decimal("5000.00"), "OpeningCreditBalance": Decimal("0.00"), "ClosingDebitBalance": Decimal("0.00"), "ClosingCreditBalance": Decimal("0.00"), "GroupingCategory": models.GroupingCategoryEnum.GM, "TaxonomyCode": 4111},
            {"AccountID": "611001", "AccountDescription": "CMVMC (Demo)", "OpeningDebitBalance": Decimal("0.00"), "OpeningCreditBalance": Decimal("0.00"), "ClosingDebitBalance": Decimal("0.00"), "ClosingCreditBalance": Decimal("0.00"), "GroupingCategory": models.GroupingCategoryEnum.GM, "TaxonomyCode": 311},
            {"AccountID": "711001", "AccountDescription": "Vendas Mercadorias (Demo)", "OpeningDebitBalance": Decimal("0.00"), "OpeningCreditBalance": Decimal("0.00"), "ClosingDebitBalance": Decimal("0.00"), "ClosingCreditBalance": Decimal("0.00"), "GroupingCategory": models.GroupingCategoryEnum.GM, "TaxonomyCode": 711},
        ]
        for acc_data in demo_gl_accounts_data:
            db.add(models.Account(**acc_data)) # models.Account is GeneralLedgerAccountSQLModel
        logger.info(f"Added {len(demo_gl_accounts_data)} global demo GL accounts.")
    else:
        logger.info("GeneralLedgerAccounts table is not empty. Skipping global demo GL account population.")

    try:
        db.commit()
        logger.info(f"Demo data population commit successful for user '{demo_user.username}'.")
    except Exception as e:
        logger.error(f"Error committing demo data for user '{demo_user.username}': {e}", exc_info=True)
        db.rollback()


if __name__ == '__main__':
    # This example requires a database engine and session.
    # It's best tested through the application startup or dedicated tests.
    print("--- Demo Data Population (Illustrative - Requires DB Setup) ---")
    # from database import engine as main_engine, create_db_and_tables as main_create_db
    # from sqlmodel import SQLModel
    #
    # if "sqlite" not in str(main_engine.url):
    #     print("Skipping demo data example as DB is not SQLite.")
    # else:
    #     print(f"Using database: {main_engine.url}")
    #     # Ensure tables are created (idempotent)
    #     # In a real app, User model needs to be imported for metadata for create_all
    #     # from models import User # Ensure User model is known to SQLModel.metadata
    #     SQLModel.metadata.create_all(main_engine) 
    #
    #     with Session(main_engine) as session:
    #         print("1. Creating or getting demo user...")
    #         demo_user_instance = create_demo_user(session)
    #         if demo_user_instance:
    #             print(f"Demo user: {demo_user_instance.username} (ID: {demo_user_instance.id}, Active: {demo_user_instance.is_active})")
    #             print("\n2. Populating demo data (if needed)...")
    #             populate_demo_data(session, demo_user_instance)
    #             print("\nDemo data population process finished.")
    #
    #             # Verify (optional manual check)
    #             # customers = session.exec(select(models.Customer).where(models.Customer.owner_id == demo_user_instance.id)).all()
    #             # print(f"Number of customers for demo user: {len(customers)}")
    #             # if customers:
    #             #     print(f"First demo customer: {customers[0].CompanyName}")
    #         else:
    #             print("Failed to create or retrieve demo user.")

    print("\nNote: Run application or tests to see demo data in action.")
    print("--- End of Demo Data Population ---")
