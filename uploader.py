import csv
from typing import List, Dict, Any

def read_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Reads a CSV file and returns its content as a list of dictionaries.

    Each dictionary in the list represents a row, with column headers as keys.

    Args:
        file_path: The path to the CSV file.

    Returns:
        A list of dictionaries, where each dictionary represents a row.
        Returns an empty list if the CSV is empty or only contains a header row.
    
    Raises:
        FileNotFoundError: If the CSV file does not exist.
        ValueError: If there's an issue decoding the file or a CSV formatting error.
    """
    rows: List[Dict[str, Any]] = []
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8-sig') as csvfile:
            # 'utf-8-sig' handles CSVs with a Byte Order Mark (BOM)
            reader = csv.DictReader(csvfile)
            if not reader.fieldnames:
                # Handle empty file or file with no headers
                return []
            for row in reader:
                rows.append(row)
        return rows
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at: {file_path}")
    except UnicodeDecodeError:
        raise ValueError(f"Encoding issue with CSV file: {file_path}. Please ensure it's UTF-8 encoded.")
    except csv.Error as e:
        raise ValueError(f"Error reading CSV file {file_path}: {e}")
    except Exception as e:
        raise ValueError(f"An unexpected error occurred while reading CSV {file_path}: {e}")

if __name__ == '__main__':
    # Example usage (optional, for testing purposes)
    try:
        # Ensure 'sample_data' directory and the file exist when running this directly
        sample_csv_path = 'sample_data/sample_customers.csv'
        # Create a dummy CSV for direct testing if needed
        # This is just to ensure the main block runs without manual file creation during dev
        try:
            with open(sample_csv_path, 'r') as f:
                if not f.read().strip(): # if file is empty or whitespace
                    raise FileNotFoundError 
        except FileNotFoundError:
             with open(sample_csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Client ID", "Company Name", "Tax ID"])
                writer.writerow(["T001", "Test Corp", "TX123"])

        data = read_csv_file(sample_csv_path)
        if data:
            print(f"Successfully read {len(data)} rows from {sample_csv_path}.")
            print("First row:", data[0])
        else:
            print(f"No data or only headers found in {sample_csv_path}.")
    except Exception as e:
        print(f"Error in example usage: {e}")
