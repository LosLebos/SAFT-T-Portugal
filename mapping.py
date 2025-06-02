import json
from typing import Dict, Any, List, Type
from pydantic import BaseModel, ValidationError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MappingProfile(BaseModel):
    """
    Defines the structure for a mapping profile.
    - profile_name: A user-friendly name for the mapping.
    - target_model: The name of the SAF-T Pydantic model this profile targets (e.g., "Customer").
    - mappings: A dictionary where keys are source CSV column headers
                and values are the corresponding target fields in the Pydantic model.
                Nested fields can be specified using dot notation (e.g., "BillingAddress.AddressDetail").
    """
    profile_name: str
    target_model: str
    mappings: Dict[str, str]

# The set_nested_value function is no longer needed as Pydantic's model_validate (or __init__)
# handles nested dictionary structures effectively for instantiation.

def apply_mapping(data_rows: List[Dict[str, Any]], mapping_profile: MappingProfile, available_models: Dict[str, Type[BaseModel]]) -> List[BaseModel]:
    """
    Applies mapping rules to transform raw data rows into Pydantic model instances.

    Args:
        data_rows: A list of dictionaries, where each dictionary represents a row of data.
        mapping_profile: The MappingProfile object containing transformation rules.
        available_models: A dictionary mapping model names (e.g., "Customer") to Pydantic model classes.

    Returns:
        A list of populated Pydantic model instances.
    """
    populated_models: List[BaseModel] = []
    TargetModel = available_models.get(mapping_profile.target_model)

    if not TargetModel:
        logger.error(f"Target model '{mapping_profile.target_model}' not found in available_models.")
        raise ValueError(f"Target model '{mapping_profile.target_model}' not found in available_models dictionary.")

    for i, row_data in enumerate(data_rows):
        model_dict_data = {}
        for csv_column, model_path in mapping_profile.mappings.items():
            if csv_column not in row_data:
                logger.warning(f"Row {i+1}: CSV column '{csv_column}' defined in mapping not found in source data. This mapping will be skipped for this row.")
                continue

            value = row_data[csv_column]
            parts = model_path.split('.')
            current_level = model_dict_data
            for part_index, part in enumerate(parts[:-1]):
                if part not in current_level:
                    current_level[part] = {}
                elif not isinstance(current_level[part], dict):
                    logger.error(f"Row {i+1}: Mapping conflict or invalid structure for path '{model_path}' at part '{part}'. Expected a dictionary, found {type(current_level[part])}.")
                    # Skip this problematic mapping for this row or handle error more gracefully
                    current_level = None # Mark as problematic
                    break 
                current_level = current_level[part]
            
            if current_level is not None:
                final_field = parts[-1]
                current_level[final_field] = value
            else:
                # Error was logged above, skip this entire model_path for this row
                continue
        
        if not model_dict_data:
            logger.warning(f"Row {i+1}: No data was mapped for target model '{mapping_profile.target_model}'. Skipping instance creation for this row.")
            continue

        try:
            # Pydantic's model_validate (v2) or __init__ (v1/v2) handles nested dicts for instantiation
            instance = TargetModel.model_validate(model_dict_data) # For Pydantic v2
            # For Pydantic v1, it would be: instance = TargetModel(**model_dict_data)
            populated_models.append(instance)
        except ValidationError as e:
            logger.error(f"Row {i+1}: Validation error creating instance of '{mapping_profile.target_model}' from mapped data {model_dict_data}. Error: {e}")
        except Exception as e: # Catch other unexpected errors during instantiation
            logger.error(f"Row {i+1}: Unexpected error creating instance of '{mapping_profile.target_model}' from {model_dict_data}. Error: {e}")
            
    return populated_models


def load_mapping_profile(profile_path: str) -> MappingProfile:
    """
    Loads a mapping profile from a JSON file.

    Args:
        profile_path: The path to the JSON mapping profile file.

    Returns:
        An instance of MappingProfile.
    """
    try:
        with open(profile_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return MappingProfile(**data)
    except FileNotFoundError:
        logger.error(f"Mapping profile not found at: {profile_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from mapping profile {profile_path}: {e}")
        raise ValueError(f"Error decoding JSON from mapping profile: {profile_path}") from e
    except ValidationError as e:
        logger.error(f"Validation error loading mapping profile {profile_path}: {e}")
        raise ValueError(f"Invalid mapping profile format {profile_path}: {e}") from e
    except Exception as e:
        logger.error(f"Unexpected error loading mapping profile {profile_path}: {e}")
        raise ValueError(f"Error loading mapping profile {profile_path}: {e}") from e

if __name__ == '__main__':
    # Example usage (optional, for local testing)
    # This example assumes models.py and sample_data are accessible
    # from the directory where mapping.py is located or PYTHONPATH is set.
    
    # Due to sandbox limitations, direct import from models.py might be tricky here.
    # The test environment will handle imports correctly.
    # For standalone execution, you might need to adjust sys.path or run as a module.

    print("Attempting example usage of mapping.py...")
    # Define a dummy Customer model for the example if models.py is not directly accessible
    class DummyAddress(BaseModel):
        AddressDetail: str
        City: str
        PostalCode: str
        Country: str

    class DummyCustomer(BaseModel):
        CustomerID: str
        CompanyName: str
        BillingAddress: DummyAddress
        CustomerTaxID: str
        SelfBillingIndicator: int = 0 # Example default

    available_test_models = {"Customer": DummyCustomer}
    
    sample_rows = [
        {"Client ID": "C001", "Company Name": "ABC Corp", "Billing Address": "123 Main St", "City": "Anytown", "Postal Code": "12345", "Country": "US", "Tax ID": "US123456789", "SelfBilling": "1"},
        {"Client ID": "C002", "Company Name": "XYZ Inc", "Billing Address": "456 Oak Ave", "City": "Otherville", "Postal Code": "67890", "Country": "CA", "Tax ID": "CA987654321", "SelfBilling": "0"}
    ]

    # Path assumes script is run from repository root or sample_data is in the same dir.
    # For sandbox, use a relative path that's known to exist or create it.
    # The test_mapping.py will use a controlled sample profile.
    
    # Create a dummy profile for direct testing if sample_data is not found
    example_profile_path = 'example_mapping_profile.json'
    with open(example_profile_path, 'w') as f:
        json.dump({
            "profile_name": "Example Customer Mapping",
            "target_model": "Customer",
            "mappings": {
                "Client ID": "CustomerID",
                "Company Name": "CompanyName",
                "Billing Address": "BillingAddress.AddressDetail",
                "City": "BillingAddress.City",
                "Postal Code": "BillingAddress.PostalCode",
                "Country": "BillingAddress.Country",
                "Tax ID": "CustomerTaxID",
                "SelfBilling": "SelfBillingIndicator"
            }
        }, f)

    try:
        print(f"Loading profile: {example_profile_path}")
        profile = load_mapping_profile(example_profile_path)
        print(f"Successfully loaded mapping profile: {profile.profile_name}")
        
        print("\nApplying mapping...")
        # Using DummyCustomer for this example context
        populated_customers = apply_mapping(sample_rows, profile, available_test_models)
        
        if populated_customers:
            print(f"\nSuccessfully populated {len(populated_customers)} customer models:")
            for customer_instance in populated_customers:
                print(customer_instance.model_dump_json(indent=2))
        else:
            print("\nNo models were populated. Check logs for errors.")

    except Exception as e:
        print(f"Error in example usage: {e}")
    finally:
        if os.path.exists(example_profile_path):
            os.remove(example_profile_path)
