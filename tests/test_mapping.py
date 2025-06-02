import unittest
import json
import os
import logging
from pydantic import ValidationError

# Assuming models.py is in the parent directory or accessible via PYTHONPATH
# For robust testing, ensure Python path is set up correctly or use relative imports if structured as a package.
# If mapping.py and models.py are in the same directory (e.g. after flattening by the tool):
# from models import Customer, CustomerAddressStructure, SAFPTGLAccountID, CountryType, CustomerCountry
# Otherwise, adjust path:
import sys
# This adds the parent directory to the Python path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mapping import MappingProfile, load_mapping_profile, apply_mapping
from models import Customer, CustomerAddressStructure, Header, AuditFile # Import specific models needed for testing

# Disable logging for most tests to keep output clean, enable for debugging if needed
logging.disable(logging.CRITICAL)


class TestMapping(unittest.TestCase):

    # Sample data for load_mapping_profile tests
    sample_mapping_data_json = {
        "profile_name": "Test Customer Mapping",
        "target_model": "Customer",
        "mappings": {
            "Client ID": "CustomerID",
            "Company Name": "CompanyName",
            "Address Line 1": "BillingAddress.AddressDetail",
            "City": "BillingAddress.City",
            "Zip": "BillingAddress.PostalCode",
            "Country Code": "BillingAddress.Country",
            "VAT Number": "CustomerTaxID",
            "Account Ref": "AccountID",
            "Self Bill": "SelfBillingIndicator"
        }
    }
    test_profile_path = "test_sample_mapping_profile.json"

    # Sample data for apply_mapping tests
    sample_customer_rows = [
        {
            "Client ID": "C001", "Company Name": "Tech Solutions Ltd.", 
            "Address Line 1": "123 Cybernetic Road", "City": "Digi-Ville", 
            "Zip": "DV123", "Country Code": "PT", "VAT Number": "PT501234567",
            "Account Ref": "ACC001", "Self Bill": "1"
        },
        {
            "Client ID": "C002", "Company Name": "Green Energy Co.", 
            "Address Line 1": "45 Eco Park", "City": "Terra Firm", 
            "Zip": "TF456", "Country Code": "US", "VAT Number": "US987654321", # Example non-PT NIF
            "Account Ref": "Desconhecido", "Self Bill": "0" # 'Desconhecido' for AccountID
        },
        { # Row with a missing column that's mapped
            "Client ID": "C003", "Company Name": "Ephemeral Creations", 
            "Address Line 1": "789 Dream St", "City": "Nod", 
            "Zip": "ND789", "Country Code": "GB", # VAT Number is missing
            "Account Ref": "ACC003", "Self Bill": "0"
        },
        { # Row that will cause a validation error (e.g. invalid country code for CustomerCountry)
            "Client ID": "C004", "Company Name": "Error Prone Inc.", 
            "Address Line 1": "1 Error Lane", "City": "Faultsville", 
            "Zip": "FV000", "Country Code": "INVALID", "VAT Number": "PT111222333",
            "Account Ref": "ACC004", "Self Bill": "0"
        }
    ]

    available_models_for_test = {
        "Customer": Customer,
        "Header": Header 
        # Add other models if new test cases require them
    }

    @classmethod
    def setUpClass(cls):
        with open(cls.test_profile_path, 'w') as f:
            json.dump(cls.sample_mapping_data_json, f)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.test_profile_path):
            os.remove(cls.test_profile_path)

    def test_load_mapping_profile_success(self):
        profile = load_mapping_profile(self.test_profile_path)
        self.assertIsInstance(profile, MappingProfile)
        self.assertEqual(profile.profile_name, self.sample_mapping_data_json["profile_name"])
        self.assertEqual(profile.target_model, self.sample_mapping_data_json["target_model"])
        self.assertEqual(profile.mappings, self.sample_mapping_data_json["mappings"])

    def test_load_mapping_profile_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            load_mapping_profile("non_existent_profile.json")

    def test_load_mapping_profile_invalid_json(self):
        invalid_json_path = "invalid_profile.json"
        with open(invalid_json_path, 'w') as f:
            f.write("{'name': 'test', ") # Malformed JSON
        with self.assertRaises(ValueError) as context:
            load_mapping_profile(invalid_json_path)
        self.assertIn("Error decoding JSON", str(context.exception))
        os.remove(invalid_json_path)

    def test_load_mapping_profile_missing_fields_in_json(self):
        incomplete_data = {"profile_name": "Incomplete"} # Missing target_model, mappings
        incomplete_profile_path = "incomplete_profile.json"
        with open(incomplete_profile_path, 'w') as f:
            json.dump(incomplete_data, f)
        with self.assertRaises(ValueError) as context: # Pydantic's ValidationError is caught and re-raised as ValueError
            load_mapping_profile(incomplete_profile_path)
        self.assertIn("Invalid mapping profile format", str(context.exception)) # Check for our custom error message
        os.remove(incomplete_profile_path)

    # Tests for apply_mapping
    def test_apply_mapping_success_customer(self):
        profile = MappingProfile(**self.sample_mapping_data_json)
        # Use first two rows which are valid
        valid_rows = [self.sample_customer_rows[0], self.sample_customer_rows[1]] 
        
        results = apply_mapping(valid_rows, profile, self.available_models_for_test)
        
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], Customer)
        self.assertEqual(results[0].CustomerID, "C001")
        self.assertEqual(results[0].CompanyName, "Tech Solutions Ltd.")
        self.assertIsInstance(results[0].BillingAddress, CustomerAddressStructure)
        self.assertEqual(results[0].BillingAddress.AddressDetail, "123 Cybernetic Road")
        self.assertEqual(results[0].BillingAddress.City, "Digi-Ville")
        self.assertEqual(results[0].BillingAddress.PostalCode, "DV123")
        # Pydantic should coerce "PT" to the CustomerCountry type.
        # If CustomerCountry was a strict Literal/Enum, this would need to match exactly.
        # Our current CustomerCountry validates if it's 2-char upper or "Desconhecido"
        self.assertEqual(results[0].BillingAddress.Country, "PT") 
        self.assertEqual(results[0].CustomerTaxID, "PT501234567")
        self.assertEqual(results[0].AccountID, "ACC001") # Validated by SAFPTGLAccountID
        self.assertEqual(results[0].SelfBillingIndicator, 1)


        self.assertIsInstance(results[1], Customer)
        self.assertEqual(results[1].CustomerID, "C002")
        self.assertEqual(results[1].BillingAddress.Country, "US")
        self.assertEqual(results[1].AccountID, "Desconhecido") # Allowed value

    def test_apply_mapping_target_model_not_available(self):
        profile_data = self.sample_mapping_data_json.copy()
        profile_data["target_model"] = "NonExistentModel"
        profile = MappingProfile(**profile_data)
        with self.assertRaises(ValueError) as context:
            apply_mapping(self.sample_customer_rows, profile, self.available_models_for_test)
        self.assertIn("Target model 'NonExistentModel' not found", str(context.exception))

    def test_apply_mapping_missing_source_column_gracefully_skips_field(self):
        # This test relies on the logging inside apply_mapping.
        # The function should skip the mapping for the missing column and proceed.
        profile = MappingProfile(**self.sample_mapping_data_json)
        # Row 3 is missing "VAT Number"
        # Row 1 is complete
        test_rows = [self.sample_customer_rows[0], self.sample_customer_rows[2]] 
        
        # Temporarily enable logging to check warnings
        logging.disable(logging.NOTSET)
        with self.assertLogs(logger='mapping', level='WARNING') as log_watcher:
            results = apply_mapping(test_rows, profile, self.available_models_for_test)
        logging.disable(logging.CRITICAL) # Disable again

        self.assertEqual(len(results), 2) # Both rows should still produce a model instance
        
        # First customer should be complete
        self.assertEqual(results[0].CustomerID, "C001")
        self.assertIsNotNone(results[0].CustomerTaxID)

        # Second customer (from row 3) will be missing CustomerTaxID as it wasn't in the source row
        # Pydantic models set fields to None if not provided and not required with a default.
        # CustomerTaxID is mandatory in the model (SAFPTtextTypeMandatoryMax30Car)
        # So, this row should actually fail Pydantic validation if CustomerTaxID is truly missing
        # Let's re-evaluate: if a *mapped* field is mandatory in Pydantic and the CSV column is missing,
        # then Pydantic validation *should* fail for that instance.
        # The current apply_mapping logs a warning and continues, then Pydantic validation would fail.
        # This means results[1] in this case should not exist if CustomerTaxID is mandatory.

        # Corrected expectation: The row that would be missing a mandatory field due to a missing
        # CSV column should fail validation and not be included in the results.
        # The apply_mapping function's try-except block around TargetModel.model_validate()
        # would catch this ValidationError.

        # Let's re-run with the expectation that only the valid row is processed.
        # We need to check the logs for the validation error of the second row.
        logging.disable(logging.NOTSET) # Enable logs for this section
        with self.assertLogs(logger='mapping', level='ERROR') as error_log_watcher: # Expecting ERROR for validation failure
            results_strict = apply_mapping([self.sample_customer_rows[2]], profile, self.available_models_for_test)
        logging.disable(logging.CRITICAL)
        
        self.assertEqual(len(results_strict), 0) # The instance for C003 should fail validation
        
        found_error_log = False
        for record in error_log_watcher.records:
            if "C003" in record.getMessage() and "CustomerTaxID" in record.getMessage() and "Field required" in record.getMessage() : # Pydantic v2 message
                found_error_log = True
                break
        self.assertTrue(found_error_log, "Expected validation error log for missing CustomerTaxID for C003 was not found.")


    def test_apply_mapping_validation_error_for_row(self):
        # Row 4 has "Country Code": "INVALID" which should fail CustomerCountry validation
        profile = MappingProfile(**self.sample_mapping_data_json)
        test_rows = [self.sample_customer_rows[3]] # Only the error-prone row

        logging.disable(logging.NOTSET) # Enable logs
        with self.assertLogs(logger='mapping', level='ERROR') as log_watcher:
            results = apply_mapping(test_rows, profile, self.available_models_for_test)
        logging.disable(logging.CRITICAL)

        self.assertEqual(len(results), 0) # This row should fail validation
        
        found_log = False
        for record in log_watcher.records:
            if "C004" in record.getMessage() and "BillingAddress.Country" in record.getMessage(): # Check that the error is related to the expected field
                found_log = True
                break
        self.assertTrue(found_log, "Expected validation error log for C004's country code was not found.")

    def test_apply_mapping_empty_data_rows(self):
        profile = MappingProfile(**self.sample_mapping_data_json)
        results = apply_mapping([], profile, self.available_models_for_test)
        self.assertEqual(len(results), 0)

    def test_apply_mapping_incorrect_field_path_in_mapping(self):
        # If a model_path in mappings doesn't exist on the Pydantic model,
        # Pydantic's model_validate will raise a ValidationError because
        # it receives an unexpected field in the input dictionary.
        profile_data = self.sample_mapping_data_json.copy()
        profile_data["mappings"]["NonExistentHeader"] = "NonExistentField.SubField"
        profile = MappingProfile(**profile_data)
        
        test_row_with_extra_header = [
            {
                "Client ID": "C005", "Company Name": "Field Path Test", 
                "Address Line 1": "1 Test St", "City": "Testville", 
                "Zip": "TS123", "Country Code": "PT", "VAT Number": "PT601234567",
                "Account Ref": "ACC005", "Self Bill": "0",
                "NonExistentHeader": "some_value" # Data for the bad mapping
            }
        ]
        logging.disable(logging.NOTSET)
        # Expect an ERROR log because Pydantic will complain about "NonExistentField"
        with self.assertLogs(logger='mapping', level='ERROR') as error_log_watcher:
            results = apply_mapping(test_row_with_extra_header, profile, self.available_models_for_test)
        logging.disable(logging.CRITICAL)
        
        self.assertEqual(len(results), 0) # Should fail validation due to unexpected field "NonExistentField"
        
        found_error = False
        for record in error_log_watcher.records:
            # Pydantic v2: "Unexpected keyword argument `NonExistentField`" or similar if it's a top-level field.
            # If it's nested like "NonExistentField.SubField", the error might be about "NonExistentField"
            # not being a valid field for the model that would contain it, or if it's at the root,
            # "Unexpected keyword argument" for the root model.
            # The current apply_mapping creates a dict like {'NonExistentField': {'SubField': 'some_value'}}
            # So TargetModel(**data) would complain about 'NonExistentField'.
            if "C005" in record.getMessage() and ("NonExistentField" in record.getMessage() or "Unexpected keyword argument" in record.getMessage()):
                found_error = True
                break
        self.assertTrue(found_error, "Expected error log for non-existent field path was not found.")


if __name__ == '__main__':
    # This allows running the tests directly from the command line
    # Ensure that the script can find 'mapping.py' and 'models.py'
    # If they are in the parent directory:
    if not any(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')) in p for p in sys.path):
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # It seems the tool might place all files in the root, so direct imports might work eventually.
    # The sys.path manipulation above is a common strategy when running tests in a subfolder.

    unittest.main()
