from typing import Generator
from sqlmodel import create_engine, SQLModel, Session
import logging

DATABASE_URL = "sqlite:///saft_data.db"
# For testing, one might use: "sqlite:///:memory:"
# DATABASE_URL = "sqlite:///:memory:" 

# The connect_args is recommended for SQLite to ensure proper handling of multithreading.
# It's essential for web applications but good practice for other uses too.
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

logger = logging.getLogger(__name__)

def create_db_and_tables():
    """
    Creates the database and all tables defined by SQLModel metadata.
    This function should be called once when the application starts.
    """
    logger.info("Initializing database and creating tables...")
    try:
        # SQLModel.metadata.create_all() will create tables for all imported models
        # that inherit from SQLModel and have table=True.
        # Ensure all such models are imported before this call if they are in different files.
        # For this project, models.py will contain all table definitions.
        # We might need to ensure models are loaded for SQLModel.metadata to be populated.
        # A common pattern is to import all model modules here or in a central models package __init__.
        
        # --- Import models that should be created as tables ---
        # This is crucial: SQLModel.metadata.create_all only knows about models it has "seen"
        # (i.e., classes that have been defined and inherited from SQLModel).
        # If models.py is structured such that simply importing it defines all table models, that's enough.
        # Alternatively, explicitly import them:
        import models # Make sure this import brings all SQLModels into scope

        SQLModel.metadata.create_all(engine)
        logger.info("Database and tables created successfully (if they didn't exist).")
    except Exception as e:
        logger.error(f"Error creating database or tables: {e}", exc_info=True)
        raise

def get_session() -> Generator[Session, None, None]:
    """
    Provides a database session context.
    This is a generator function to be used with `with ... :` statement or `Depends` in FastAPI.
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit() # Commit changes if no exceptions during session usage
        except Exception as e:
            logger.error(f"Error during database session: {e}", exc_info=True)
            session.rollback() # Rollback on error
            raise
        finally:
            session.close() # Session is closed automatically by context manager, but explicit can be here

if __name__ == "__main__":
    # Example of how to initialize the database directly if needed.
    # In a real application, this would be part of the app startup sequence.
    print("Attempting to create database and tables directly from database.py...")
    try:
        create_db_and_tables()
        print("Database and tables should be ready now (check saft_data.db).")

        # Example: Add a dummy record (requires a SQLModel model)
        # from sqlmodel import Field # (within a dummy model for this example)
        # class TestItem(SQLModel, table=True):
        # id: Optional[int] = Field(default=None, primary_key=True)
        # name: str
        #
        # with get_session() as session:
        # item = TestItem(name="Test DB Item")
        # session.add(item)
        # session.commit()
        # print("Dummy item added.")

    except Exception as e:
        print(f"Error during direct database setup: {e}")

    print("Note: For actual data operations, ensure your SQLModel models in models.py are correctly defined.")
