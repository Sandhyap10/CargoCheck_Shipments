
import re


def get_value(document, field):
    """Get a field value from an extracted document."""
    if not document or field not in document:
        return None

    result = document[field]

    if isinstance(result, dict):
        return result.get("value")

    return result


def normalize_number(value):
    """Extract a numeric value, e.g. '3,120 kg' becomes 3120."""
    if value is None:
        return None

    cleaned = str(value).replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)

    return float(match.group()) if match else None


def normalize_text(value):
    """Normalize text for basic comparison."""
    if value is None:
        return None

    return " ".join(str(value).lower().split())


def compare_numeric_field(
    field_name,
    documents,
    document_types,
    tolerance=0,
    severity="HIGH"
):
    values = {}

    for doc_type in document_types:
        value = get_value(documents.get(doc_type), field_name)
        number = normalize_number(value)

        if number is not None:
            values[doc_type] = number

    if len(values) < 2:
        return {
            "field_name": field_name,
            "status": "NOT_CHECKED",
            "severity": "INFO",
            "message": "Insufficient document values for comparison",
            "compared_values": values
        }

    numbers = list(values.values())
    difference = max(numbers) - min(numbers)

    if difference <= tolerance:
        status = "MATCH"
        result_severity = "INFO"
        message = f"{field_name} matches across available documents"
    else:
        status = "MISMATCH"
        result_severity = severity
        message = (
            f"{field_name} discrepancy detected. "
            f"Difference: {difference:g}"
        )

    return {
        "field_name": field_name,
        "status": status,
        "severity": result_severity,
        "message": message,
        "compared_values": values
    }


def compare_text_field(
    field_name,
    documents,
    document_types,
    severity="MEDIUM"
):
    values = {}

    for doc_type in document_types:
        value = get_value(documents.get(doc_type), field_name)

        if value is not None and str(value).strip():
            values[doc_type] = str(value).strip()

    if len(values) < 2:
        return {
            "field_name": field_name,
            "status": "NOT_CHECKED",
            "severity": "INFO",
            "message": "Insufficient document values for comparison",
            "compared_values": values
        }

    normalized = {
        normalize_text(value) for value in values.values()
    }

    if len(normalized) == 1:
        status = "MATCH"
        result_severity = "INFO"
        message = f"{field_name} matches across available documents"
    else:
        status = "MISMATCH"
        result_severity = severity
        message = f"{field_name} differs across documents"

    return {
        "field_name": field_name,
        "status": status,
        "severity": result_severity,
        "message": message,
        "compared_values": values
    }


def compare_mapped_text_field(field_name, documents, field_mapping):
    """
    Compare different field names across documents.

    Example:
    Invoice buyer vs Bill of Lading consignee.
    """
    values = {}

    for doc_type, document_field in field_mapping.items():
        value = get_value(documents.get(doc_type), document_field)

        if value is not None and str(value).strip():
            values[doc_type] = str(value).strip()

    if len(values) < 2:
        return {
            "field_name": field_name,
            "status": "NOT_CHECKED",
            "severity": "INFO",
            "message": "Insufficient document values for comparison",
            "compared_values": values
        }

    normalized = {
        normalize_text(value) for value in values.values()
    }

    if len(normalized) == 1:
        status = "MATCH"
        severity = "INFO"
        message = f"{field_name} matches across available documents"
    else:
        status = "MISMATCH"
        severity = "MEDIUM"
        message = f"{field_name} differs across documents"

    return {
        "field_name": field_name,
        "status": status,
        "severity": severity,
        "message": message,
        "compared_values": values
    }


def validate_shipment(documents):
    results = []

    # 1. Gross weight: all three documents
    results.append(
        compare_numeric_field(
            "gross_weight",
            documents,
            [
                "Commercial Invoice",
                "Packing List",
                "Bill of Lading"
            ]
        )
    )

    # 2. Net weight: Invoice and Packing List
    results.append(
        compare_numeric_field(
            "net_weight",
            documents,
            [
                "Commercial Invoice",
                "Packing List"
            ]
        )
    )

    # 3. Quantity: Invoice and Packing List
    results.append(
        compare_numeric_field(
            "quantity",
            documents,
            [
                "Commercial Invoice",
                "Packing List"
            ],
            severity="MEDIUM"
        )
    )

    # 4. Number of packages: Packing List and Bill of Lading
    results.append(
        compare_numeric_field(
            "number_of_packages",
            documents,
            [
                "Packing List",
                "Bill of Lading"
            ],
            severity="MEDIUM"
        )
    )

    # 5. Product description: all three documents
    results.append(
        compare_text_field(
            "product_description",
            documents,
            [
                "Commercial Invoice",
                "Packing List",
                "Bill of Lading"
            ]
        )
    )

    # 6. Container number: Packing List and Bill of Lading
    results.append(
        compare_text_field(
            "container_number",
            documents,
            [
                "Packing List",
                "Bill of Lading"
            ],
            severity="HIGH"
        )
    )

    # 7. Vessel name: Packing List and Bill of Lading
    results.append(
        compare_text_field(
            "vessel_name",
            documents,
            [
                "Packing List",
                "Bill of Lading"
            ]
        )
    )
    
    # Compare voyage number between Packing List and Bill of Lading
    results.append(
        compare_text_field(
        "voyage_number",
        documents,
        [
            "Packing List",
            "Bill of Lading"
        ]
    )
)

    # 8. Consignee: Invoice buyer vs Bill of Lading consignee
    results.append(
        compare_mapped_text_field(
            "consignee",
            documents,
            {
                "Commercial Invoice": "buyer",
                "Bill of Lading": "consignee"
            }
        )
    )

    # 9. Shipper/Seller: Invoice seller vs Bill of Lading shipper
    results.append(
        compare_mapped_text_field(
            "shipper",
            documents,
            {
                "Commercial Invoice": "seller",
                "Bill of Lading": "shipper"
            }
        )
    )

    return results
