from lxml import etree
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

def validate_saft_xml(xml_string: str, xsd_filepath: str) -> Tuple[bool, List[str]]:
    """
    Validates an XML string against a given XSD schema file.

    Args:
        xml_string: The XML content as a string.
        xsd_filepath: The path to the XSD schema file.

    Returns:
        A tuple: (is_valid: bool, errors: List[str]).
        'is_valid' is True if validation succeeds, False otherwise.
        'errors' is a list of error messages if validation fails or an error occurs.
    """
    logger.info(f"Attempting to validate XML against XSD: {xsd_filepath}")

    try:
        # Parse the XSD schema file
        try:
            xmlschema_doc = etree.parse(xsd_filepath)
            xmlschema = etree.XMLSchema(xmlschema_doc)
            logger.debug(f"XSD schema '{xsd_filepath}' parsed successfully.")
        except etree.XMLSchemaParseError as e:
            logger.error(f"XSD schema file '{xsd_filepath}' could not be parsed: {e}", exc_info=True)
            return False, [f"XSD schema parse error: {e}"]
        except OSError as e: # Handles file not found
            logger.error(f"XSD schema file '{xsd_filepath}' not found or not accessible: {e}", exc_info=True)
            return False, [f"XSD file error: {e}"]

        # Parse the XML string
        # lxml.etree.fromstring expects bytes, so encode the string to UTF-8
        try:
            xml_bytes = xml_string.encode('utf-8')
            parsed_xml_doc = etree.fromstring(xml_bytes)
            logger.debug("XML string parsed successfully.")
        except etree.XMLSyntaxError as e:
            logger.error(f"Malformed XML string: {e}", exc_info=True)
            # Provide a snippet of the error location if possible, though 'e' itself is informative
            return False, [f"Malformed XML: {e}"]

        # Validate the XML document against the schema
        # xmlschema.validate(parsed_xml_doc) returns True/False
        # xmlschema.assertValid(parsed_xml_doc) raises DocumentInvalid on failure
        
        is_valid = xmlschema.validate(parsed_xml_doc)
        
        if is_valid:
            logger.info("XML validation successful.")
            return True, []
        else:
            logger.warning("XML validation failed.")
            error_messages = []
            for error in xmlschema.error_log:
                # Format: <filename>:<line>:<column>: <message> (<type_name>.<error_type_name>)
                # e.g., DOC:4:0:ERROR:SCHEMASV:SCHEMAV_ELEMENT_CONTENT: Element 'Header': Missing child element(s). Expected is ( AuditFileVersion ).
                # We want a human-readable summary.
                error_messages.append(f"L{error.line}:C{error.column} - {error.message} (Domain: {error.domain_name}, Type: {error.type_name})")
            
            if not error_messages and not is_valid : # Should not happen if validate() is False
                 error_messages.append("Unknown validation error: xmlschema.validate returned False but no errors in log.")

            logger.debug(f"Validation errors: {error_messages}")
            return False, error_messages

    except Exception as e:
        logger.error(f"An unexpected error occurred during XML validation: {e}", exc_info=True)
        return False, [f"Unexpected validation error: {e}"]

if __name__ == '__main__':
    # Example usage:
    # This requires an XSD file (e.g., SAFTPT1_04_01.xsd) and some sample XML.
    
    print("Example usage of xsd_validator.py")
    
    # Dummy XSD and XML for local testing if files aren't present
    dummy_xsd_path = "dummy_schema.xsd"
    dummy_valid_xml = "<TestRoot><TestElement>Hello</TestElement></TestRoot>"
    dummy_invalid_xml_structure = "<TestRoot><WrongElement>Bye</WrongElement></TestRoot>"
    dummy_invalid_xml_data = "<TestRoot><TestElement>12.A</TestElement></TestRoot>" # Assuming TestElement expects int

    # Create a dummy XSD file for the example
    # This XSD expects a TestRoot with a TestElement of type xs:string or xs:int for data type test
    xsd_content = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="TestRoot">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="TestElement" type="xs:string"/> 
      </xs:sequence>
    </xs:complexType>
  </xs:element>
</xs:schema>
"""
    # To test data type error, change TestElement type to xs:int in xsd_content for that specific test.
    
    with open(dummy_xsd_path, "w") as f:
        f.write(xsd_content)

    print(f"\n--- Validating: Well-formed and Valid XML ---")
    valid, errors = validate_saft_xml(dummy_valid_xml, dummy_xsd_path)
    print(f"Validation Result: {'Valid' if valid else 'Invalid'}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")

    print(f"\n--- Validating: Structurally Invalid XML ---")
    valid, errors = validate_saft_xml(dummy_invalid_xml_structure, dummy_xsd_path)
    print(f"Validation Result: {'Valid' if valid else 'Invalid'}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")

    # Modify XSD for data type test temporarily
    xsd_content_int = xsd_content.replace('type="xs:string"', 'type="xs:integer"')
    with open(dummy_xsd_path, "w") as f:
        f.write(xsd_content_int)

    print(f"\n--- Validating: Data Type Invalid XML (TestElement should be integer) ---")
    valid, errors = validate_saft_xml(dummy_invalid_xml_data, dummy_xsd_path) # "12.A" is not an int
    print(f"Validation Result: {'Valid' if valid else 'Invalid'}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")
            
    print(f"\n--- Validating: Malformed XML ---")
    malformed_xml = "<TestRoot><TestElement>Missing closing tag" 
    valid, errors = validate_saft_xml(malformed_xml, dummy_xsd_path)
    print(f"Validation Result: {'Valid' if valid else 'Invalid'}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")

    print(f"\n--- Validating: Non-existent XSD ---")
    valid, errors = validate_saft_xml(dummy_valid_xml, "non_existent.xsd")
    print(f"Validation Result: {'Valid' if valid else 'Invalid'}")
    if errors:
        print("Errors:")
        for err in errors:
            print(f"- {err}")

    # Clean up dummy XSD
    if os.path.exists(dummy_xsd_path):
        os.remove(dummy_xsd_path)
    
    print("\nNote: For real SAF-T validation, provide actual SAF-T XML and the correct XSD path.")
