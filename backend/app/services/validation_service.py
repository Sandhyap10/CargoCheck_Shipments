
import re

def get_value(document, field):
    """Get a field value from an extracted document."""
    if not document or field not in document:
        return None

    value = document[field]

    if isinstance(value, dict):
        return value.get("value")

    return value


def normalize_number(value):
    """Convert values such as '3,120 kg' into numbers."""
    if value is None:
        return None

    cleaned = str(value).replace(",", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)

    return float(match.group()) if match else None


def normalize_text(value):
    """Normalize text before comparison."""
    if value is None:
        return None

    return " ".join(str(value).lower().split())


def compare_numeric_field(
    field_name,
    documents,
    document_types,
    severity="HIGH",
    tolerance=0
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
    field_mapping,
    severity="MEDIUM"
):
    values = {}

    for doc_type, document_field in field_mapping.items():
        value = get_value(
            documents.get(doc_type),
            document_field
        )

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
        normalize_text(value)
        for value in values.values()
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


def validate_shipment(documents):
    results = []

    # 1. Product Description
    results.append(
        compare_text_field(
            "product_description",
            documents,
            {
                "Commercial Invoice": "product_description",
                "Packing List": "product_description",
                "Bill of Lading": "product_description"
            }
        )
    )

    # 2. Quantity
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

    # 3. Gross Weight
    results.append(
        compare_numeric_field(
            "gross_weight",
            documents,
            [
                "Commercial Invoice",
                "Packing List",
                "Bill of Lading"
            ],
            severity="HIGH"
        )
    )

    # 4. Net Weight
    results.append(
        compare_numeric_field(
            "net_weight",
            documents,
            [
                "Commercial Invoice",
                "Packing List"
            ],
            severity="HIGH"
        )
    )

    # 5. Consignee / Buyer
    results.append(
        compare_text_field(
            "consignee",
            documents,
            {
                "Commercial Invoice": "buyer",
                "Bill of Lading": "consignee"
            }
        )
    )

    # 6. Shipper / Seller
    results.append(
        compare_text_field(
            "shipper",
            documents,
            {
                "Commercial Invoice": "seller",
                "Bill of Lading": "shipper"
            }
        )
    )

    return results
