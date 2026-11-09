
import sys
import re
from pathlib import Path
from collections import defaultdict

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment


# Make the backend folder available for imports
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.services.document_extractor import extract_text_from_document
from app.services.field_extractor import extract_document_fields


# Dataset locations
EVALUATION_DIR = Path(__file__).resolve().parent
DATASET_DIR = (
    EVALUATION_DIR
    / "CargoCheck_Challenge_Dataset"
)

GROUND_TRUTH_FILE = (
    DATASET_DIR / "CargoCheck_Challenge_Ground_Truth.xlsx"
)
REPORT_FILE = EVALUATION_DIR / "CargoCheck_Accuracy_Report.xlsx"


DOCUMENT_FOLDERS = {
    "Commercial Invoice": "Commercial_Invoices",
    "Packing List": "Packing_Lists",
    "Bill of Lading": "Bills_of_Lading",
}


def normalize_value(value):
    """
    Normalize harmless formatting differences before comparison.
    Does not change the original values in the report.
    """
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)

    # Remove common weight units
    value = re.sub(r"\s*(kg|kgs|kilograms?)$", "", value)

    # Ignore thousands separators
    value = value.replace(",", "")

    return value.strip()


def load_ground_truth():
    """
    Read expected field values from the Excel ground-truth sheet.
    """
    if not GROUND_TRUTH_FILE.exists():
        raise FileNotFoundError(
            f"Ground truth file not found: {GROUND_TRUTH_FILE}"
        )

    workbook = load_workbook(
        GROUND_TRUTH_FILE,
        read_only=True,
        data_only=True
    )

    sheet = workbook["Ground Truth"]

    headers = [
        cell.value for cell in next(sheet.iter_rows(min_row=1, max_row=1))
    ]

    required_columns = [
        "filename",
        "shipment_id",
        "document_type",
        "field_name",
        "correct_value",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in headers
    ]

    if missing_columns:
        raise ValueError(
            f"Ground truth is missing columns: {missing_columns}"
        )

    column_indexes = {
        name: headers.index(name)
        for name in required_columns
    }

    records = []

    for row in sheet.iter_rows(min_row=2, values_only=True):
        filename = row[column_indexes["filename"]]

        if not filename:
            continue

        records.append({
            "filename": str(filename),
            "shipment_id": str(row[column_indexes["shipment_id"]]),
            "document_type": str(row[column_indexes["document_type"]]),
            "field_name": str(row[column_indexes["field_name"]]),
            "correct_value": str(
                row[column_indexes["correct_value"]] or ""
            ),
        })

    workbook.close()
    return records


def get_extracted_value(extracted_fields, field_name):
    """
    Support the existing field extractor's dictionary format:
    {
        "field_name": {
            "value": "...",
            "confidence": 0.95
        }
    }
    """
    field = extracted_fields.get(field_name)

    if field is None:
        return "", 0.0

    if isinstance(field, dict):
        return (
            str(field.get("value") or ""),
            float(field.get("confidence") or 0.0),
        )

    return str(field), 0.0


def process_document(record):
    """
    Run one PDF through the existing OCR and field extraction services.
    """
    folder = DOCUMENT_FOLDERS.get(record["document_type"])

    if not folder:
        return None, f"Unsupported document type: {record['document_type']}"

    pdf_path = DATASET_DIR / folder / record["filename"]

    if not pdf_path.exists():
        return None, f"PDF not found: {pdf_path}"

    try:
        text = extract_text_from_document(str(pdf_path))
        print("\n" + "=" * 60)
        print("DEBUG FILE:", pdf_path.name)
        print("EXTRACTED TEXT:")
        print(repr(text[:2000]))
        print("=" * 60)

        if not text.strip():
            return None, "No text extracted from document"

        extracted_fields = extract_document_fields(
            record["document_type"],
            text
        )
        print("EXTRACTED FIELDS:")
        print(extracted_fields)

        return extracted_fields, None

    except Exception as exc:
        return None, str(exc)


def style_sheet(sheet):
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="24476B")
        cell.alignment = Alignment(horizontal="center")

    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def calculate_percentage(correct, total):
    if total == 0:
        return 0.0

    return round((correct / total) * 100, 2)


def generate_report(results):
    """
    Create an Excel report with overall, document-wise,
    field-wise accuracy and individual comparisons.
    """
    workbook = Workbook()

    # Overall summary
    summary = workbook.active
    summary.title = "Overall Summary"

    correct = sum(1 for row in results if row["result"] == "CORRECT")
    total = len(results)
    incorrect = total - correct

    summary.append(["Metric", "Value"])
    summary.append(["Total evaluated fields", total])
    summary.append(["Correct fields", correct])
    summary.append(["Incorrect fields", incorrect])
    summary.append([
        "Overall extraction accuracy (%)",
        calculate_percentage(correct, total),
    ])

    summary.append([])
    summary.append(["Important", "This is a measured result on the supplied synthetic dataset."])
    summary.append([
        "Limitation",
        "It does not establish real-world accuracy across 200 historical shipments.",
    ])

    style_sheet(summary)
    summary.column_dimensions["A"].width = 38
    summary.column_dimensions["B"].width = 85

    # Document-wise accuracy
    document_sheet = workbook.create_sheet("Document Accuracy")
    document_sheet.append([
        "Document Type",
        "Total Fields",
        "Correct Fields",
        "Incorrect Fields",
        "Accuracy (%)",
    ])

    document_groups = defaultdict(list)

    for row in results:
        document_groups[row["document_type"]].append(row)

    for document_type, rows in document_groups.items():
        group_correct = sum(
            1 for row in rows if row["result"] == "CORRECT"
        )

        document_sheet.append([
            document_type,
            len(rows),
            group_correct,
            len(rows) - group_correct,
            calculate_percentage(group_correct, len(rows)),
        ])

    style_sheet(document_sheet)

    # Field-wise accuracy
    field_sheet = workbook.create_sheet("Field Accuracy")
    field_sheet.append([
        "Field Name",
        "Total Fields",
        "Correct Fields",
        "Incorrect Fields",
        "Accuracy (%)",
    ])

    field_groups = defaultdict(list)

    for row in results:
        key = f"{row['document_type']} - {row['field_name']}"
        field_groups[key].append(row)

    for field_name, rows in field_groups.items():
        group_correct = sum(
            1 for row in rows if row["result"] == "CORRECT"
        )

        field_sheet.append([
            field_name,
            len(rows),
            group_correct,
            len(rows) - group_correct,
            calculate_percentage(group_correct, len(rows)),
        ])

    style_sheet(field_sheet)

    # Individual field comparison
    detail_sheet = workbook.create_sheet("Field Comparisons")

    detail_sheet.append([
        "Filename",
        "Shipment ID",
        "Document Type",
        "Field Name",
        "Expected Value",
        "Extracted Value",
        "Confidence Score",
        "Result",
        "Error",
    ])

    for row in results:
        detail_sheet.append([
            row["filename"],
            row["shipment_id"],
            row["document_type"],
            row["field_name"],
            row["correct_value"],
            row["extracted_value"],
            row["confidence"],
            row["result"],
            row["error"],
        ])

    style_sheet(detail_sheet)

    for column, width in enumerate(
        [28, 16, 24, 26, 30, 30, 18, 16, 45],
        start=1
    ):
        detail_sheet.column_dimensions[
            chr(64 + column)
        ].width = width

    workbook.save(REPORT_FILE)


def main():
    print("\nCARGOCHECK AI - ACCURACY EVALUATION")
    print("-----------------------------------")

    records = load_ground_truth()

    print(f"Ground-truth field values: {len(records)}")

    results = []
    processed_files = {}

    for index, record in enumerate(records, start=1):

        filename = record["filename"]
        document_type = record["document_type"]

        print(
            f"[{index}/{len(records)}] "
            f"Processing {filename} - {record['field_name']}"
        )

        # Process each PDF only once
        cache_key = (document_type, filename)

        if cache_key not in processed_files:
            processed_fields, error = process_document(record)

            processed_files[cache_key] = (
                processed_fields,
                error
            )

        extracted_fields, processing_error = processed_files[cache_key]

        if processing_error:
            extracted_value = ""
            confidence = 0.0
            result = "INCORRECT"
            error_message = processing_error

        else:
            extracted_value, confidence = get_extracted_value(
                extracted_fields,
                record["field_name"]
            )

            expected = normalize_value(record["correct_value"])
            actual = normalize_value(extracted_value)

            result = (
                "CORRECT"
                if expected == actual and actual != ""
                else "INCORRECT"
            )

            error_message = ""

        results.append({
            **record,
            "extracted_value": extracted_value,
            "confidence": confidence,
            "result": result,
            "error": error_message,
        })

    generate_report(results)

    correct = sum(
        1 for row in results if row["result"] == "CORRECT"
    )

    total = len(results)
    incorrect = total - correct

    accuracy = calculate_percentage(correct, total)

    print("\nEVALUATION COMPLETE")
    print("-------------------")
    print(f"Total fields: {total}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {incorrect}")
    print(f"Extraction accuracy: {accuracy}%")
    print(f"Target: 95%")
    print(f"Report saved at: {REPORT_FILE}")


if __name__ == "__main__":
    main()
