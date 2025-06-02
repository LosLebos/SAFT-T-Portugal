from pydantic import BaseModel
from typing import List as TypingList, Union, Any, get_origin, get_args
from enum import Enum, EnumMeta
from datetime import date, datetime

# Import all Pydantic models from saft_data
from app.schemas import saft_data

# Helper to check for simple types suitable for direct mapping
SIMPLE_TYPES = (str, int, float, date, datetime, bool)

def _is_simple_type(type_hint: Any) -> bool:
    if type_hint in SIMPLE_TYPES:
        return True
    if isinstance(type_hint, EnumMeta): # Check if it's an Enum class
        return True
    if type_hint is Any:
        return True
    try:
        # This will catch Pydantic's ConstrainedStr types like EmailStr if they are subclasses of str
        if issubclass(type_hint, str):
            return True
    except TypeError:
        pass # type_hint is not a class (e.g., a generic alias already handled, or something else)
    return False

def _generate_mappable_fields_recursive(model_class: Any, prefix: str = "") -> TypingList[str]:
    """
    Recursively generates a list of mappable field paths from a Pydantic V2 model.
    """
    fields_list: TypingList[str] = []

    # Use model_fields for Pydantic V2
    if not hasattr(model_class, 'model_fields'):
        return fields_list

    for field_name, field_info in model_class.model_fields.items():
        current_path = f"{prefix}{field_name}"

        annotation_type = field_info.annotation

        origin_type = get_origin(annotation_type)
        args_types = get_args(annotation_type)

        # Current type to process after resolving Union/Optional
        type_to_process = annotation_type

        # Flag and type store for List[BaseModel]
        is_list_of_models = False
        list_item_model_type = None

        if origin_type is Union: # Handles Optional[X] (Union[X, NoneType]) and other Unions
            actual_args = [arg for arg in args_types if type(arg) is not type(None)]
            if not actual_args:
                continue
            type_to_process = actual_args[0] # Take the first non-None type
            # Re-evaluate origin and args for this chosen type_to_process
            origin_type = get_origin(type_to_process)
            args_types = get_args(type_to_process)

        if origin_type is TypingList:
            if args_types and args_types[0]: # Ensure there is an argument for the list item type
                list_item_type_candidate = args_types[0]
                # Check if the list item is a Pydantic BaseModel
                if hasattr(list_item_type_candidate, 'model_fields'):
                    is_list_of_models = True
                    list_item_model_type = list_item_type_candidate
                elif _is_simple_type(list_item_type_candidate):
                    # Convention: "Parent.ListField.index" for List[SimpleType]
                    fields_list.append(current_path + ".index")
                    continue # Path added, continue to next field in model_class
                else:
                    # List of other complex, non-model types, skip for now
                    continue
            else:
                # List without a specified item type, skip
                continue

        # Process based on determined type
        if is_list_of_models and list_item_model_type:
            # Convention: Parent.ListName.SubModelField for List[SubModel]
            fields_list.extend(_generate_mappable_fields_recursive(list_item_model_type, prefix=current_path + "."))
        elif hasattr(type_to_process, 'model_fields'): # Nested Pydantic Model (not in a list)
            fields_list.extend(_generate_mappable_fields_recursive(type_to_process, prefix=current_path + "."))
        elif _is_simple_type(type_to_process): # Simple type
            fields_list.append(current_path)
        # Other complex types (e.g. dict) are ignored for mappable fields.

    return fields_list

# Generate fields for each main section
header_model_fields = _generate_mappable_fields_recursive(saft_data.Header, prefix="Header.")
master_files_model_fields = _generate_mappable_fields_recursive(saft_data.MasterFiles, prefix="MasterFiles.")
general_ledger_model_fields = _generate_mappable_fields_recursive(saft_data.GeneralLedgerEntries, prefix="GeneralLedgerEntries.")
source_documents_model_fields = _generate_mappable_fields_recursive(saft_data.SourceDocuments, prefix="SourceDocuments.")

all_generated_fields = set()
all_generated_fields.update(header_model_fields)
all_generated_fields.update(master_files_model_fields)
all_generated_fields.update(general_ledger_model_fields)
all_generated_fields.update(source_documents_model_fields)

SAFT_MAPPABLE_FIELDS_RAW = sorted(list(all_generated_fields))

# Manual Curation/Exclusion List
EXCLUDED_FIELDS_PATTERNS = [
    "Header.AuditFileVersion",
    "GeneralLedgerEntries.NumberOfEntries",
    "GeneralLedgerEntries.TotalDebit",
    "GeneralLedgerEntries.TotalCredit",
    "SourceDocuments.SalesInvoices.NumberOfEntries",
    "SourceDocuments.SalesInvoices.TotalDebit",
    "SourceDocuments.SalesInvoices.TotalCredit",
    "SourceDocuments.MovementOfGoods.NumberOfMovementLines",
    "SourceDocuments.MovementOfGoods.TotalQuantityIssued",
    "SourceDocuments.WorkingDocuments.NumberOfEntries",
    "SourceDocuments.WorkingDocuments.TotalDebit",
    "SourceDocuments.WorkingDocuments.TotalCredit",
    "SourceDocuments.Payments.NumberOfEntries",
    "SourceDocuments.Payments.TotalDebit",
    "SourceDocuments.Payments.TotalCredit",
    ".DocumentTotals.TaxPayable", # Calculated totals
    ".DocumentTotals.NetTotal",
    ".DocumentTotals.GrossTotal",
    ".Hash", # Calculated Hashes
    ".HashControl",
    ".SystemEntryDate", # Often system-generated
    # Placeholder models if they resolve to paths with no actual fields under them
    "GeneralLedgerEntries.Journal.Transaction.Lines", # TransactionLines is a placeholder
    "SourceDocuments.SalesInvoices.Invoice.DocumentStatus", # If DocumentStatus itself is not a leaf node but its children are
    "SourceDocuments.MovementOfGoods.StockMovement.DocumentStatus",
    "SourceDocuments.WorkingDocuments.WorkDocument.DocumentStatus",
    "SourceDocuments.Payments.Payment.DocumentStatus",
]

# Apply exclusions more carefully
CURATED_SAFT_MAPPABLE_FIELDS = []
for field_path in SAFT_MAPPABLE_FIELDS_RAW:
    is_excluded = False
    for pattern in EXCLUDED_FIELDS_PATTERNS:
        if pattern.startswith(".") and field_path.endswith(pattern): # For general sub-fields like ".Hash"
            is_excluded = True
            break
        elif not pattern.startswith(".") and field_path == pattern: # For exact full path matches
            is_excluded = True
            break
        # Add more specific pattern matching if needed, e.g., regex or startswith for sections
    if not is_excluded:
        CURATED_SAFT_MAPPABLE_FIELDS.append(field_path)

SAFT_MAPPABLE_FIELDS = CURATED_SAFT_MAPPABLE_FIELDS

def get_mappable_fields() -> TypingList[str]:
    return SAFT_MAPPABLE_FIELDS
