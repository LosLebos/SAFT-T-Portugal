import unittest
import csv
import os
from uploader import read_csv_file

class TestUploader(unittest.TestCase):

    sample_csv_data_standard = [
        {"Client ID": "C001", "Company Name": "ABC Corp", "Tax ID": "US123456789"},
        {"Client ID": "C002", "Company Name": "XYZ Inc", "Tax ID": "US987654321"}
    ]
    test_csv_path_standard = "test_sample_customers_standard.csv"

    sample_csv_data_empty = []
    test_csv_path_empty = "test_empty.csv"
    
    sample_csv_data_header_only = []
    test_csv_path_header_only = "test_header_only.csv"


    @classmethod
    def setUpClass(cls):
        # Create a temporary standard CSV file for testing
        with open(cls.test_csv_path_standard, 'w', newline='', encoding='utf-8') as f:
            if cls.sample_csv_data_standard:
                writer = csv.DictWriter(f, fieldnames=cls.sample_csv_data_standard[0].keys())
                writer.writeheader()
                writer.writerows(cls.sample_csv_data_standard)
        
        # Create an empty CSV file
        with open(cls.test_csv_path_empty, 'w', newline='', encoding='utf-8') as f:
            pass # Just create the file

        # Create a CSV with only headers
        with open(cls.test_csv_path_header_only, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name", "Value"])


    @classmethod
    def tearDownClass(cls):
        # Remove temporary files
        if os.path.exists(cls.test_csv_path_standard):
            os.remove(cls.test_csv_path_standard)
        if os.path.exists(cls.test_csv_path_empty):
            os.remove(cls.test_csv_path_empty)
        if os.path.exists(cls.test_csv_path_header_only):
            os.remove(cls.test_csv_path_header_only)

    def test_read_csv_file_success_standard(self):
        """Test reading a standard, valid CSV file."""
        data = read_csv_file(self.test_csv_path_standard)
        self.assertEqual(data, self.sample_csv_data_standard)

    def test_read_csv_file_file_not_found(self):
        """Test reading a non-existent CSV file."""
        with self.assertRaises(FileNotFoundError):
            read_csv_file("non_existent_data.csv")

    def test_read_csv_file_empty_file(self):
        """Test reading an empty CSV file."""
        # csv.DictReader on an empty file returns an empty list, fieldnames is None
        data = read_csv_file(self.test_csv_path_empty)
        self.assertEqual(data, self.sample_csv_data_empty)

    def test_read_csv_file_header_only(self):
        """Test reading a CSV file with only a header row."""
        data = read_csv_file(self.test_csv_path_header_only)
        self.assertEqual(data, self.sample_csv_data_header_only)

    def test_read_csv_file_malformed(self):
        """Test reading a malformed CSV file."""
        malformed_csv_path = "malformed.csv"
        # Create a CSV with inconsistent number of columns (malformed)
        with open(malformed_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["ID", "Name"])
            writer.writerow(["1", "Test1", "ExtraField"]) # Malformed row
            writer.writerow(["2", "Test2"])

        # Depending on the exact nature of malformation and CSV dialect,
        # csv.DictReader might still process it, possibly with missing fields or by
        # using None for missing fields if fieldnames are explicitly passed to DictReader.
        # For now, our read_csv_file uses the header row to determine fieldnames.
        # A row with too many fields vs header will be processed by DictReader,
        # the extra fields might be put into a None key or ignored depending on Python version/csv behavior.
        # A row with too few fields will have None for the missing field values.
        # Let's test a specific type of malformed error if possible, e.g. unescaped quotes.
        
        # Test with unescaped quotes which should raise csv.Error
        csv_with_unescaped_quote = "unescaped_quote.csv"
        with open(csv_with_unescaped_quote, 'w', newline='', encoding='utf-8') as f:
            f.write('Header1,Header2\nValue1,"Value with " unescaped quote"\n')
        
        with self.assertRaises(ValueError) as context: # csv.Error is caught and re-raised as ValueError
           read_csv_file(csv_with_unescaped_quote)
        self.assertIn("Error reading CSV file", str(context.exception))

        if os.path.exists(malformed_csv_path):
            os.remove(malformed_csv_path)
        if os.path.exists(csv_with_unescaped_quote):
            os.remove(csv_with_unescaped_quote)
            
    def test_read_csv_with_utf_8_bom(self):
        """Test reading a CSV file with UTF-8 BOM."""
        bom_csv_path = "bom_test.csv"
        # Manually write bytes for UTF-8 BOM (\xef\xbb\xbf)
        with open(bom_csv_path, 'wb') as f:
            f.write(b'\xef\xbb\xbf')
            f.write(b'ID,Name\n')
            f.write(b'1,Test BOM\n')
        
        data = read_csv_file(bom_csv_path)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0], {"ID": "1", "Name": "Test BOM"})
        
        if os.path.exists(bom_csv_path):
            os.remove(bom_csv_path)


if __name__ == '__main__':
    unittest.main()
