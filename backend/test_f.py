
from app.services.field_extractor import extract_document_fields

tests = [
    ("Commercial Invoice", "Inv. No.: INV-101", "invoice_number"),
    ("Commercial Invoice", "Invoice # = INV-102", "invoice_number"),
    ("Commercial Invoice", "Date of Invoice: 09-11-2026", "invoice_date"),
    ("Commercial Invoice", "G.W.: 585 kg", "gross_weight"),
    ("Commercial Invoice", "N.W.: 530 kg", "net_weight"),
    ("Packing List", "No. of Pkgs: 35", "number_of_packages"),
    ("Packing List", "Seal #: SL884512", "seal_number"),
    ("Bill of Lading", "BOL No: BOL-2026-001", "bill_of_lading_number"),
    ("Bill of Lading", "BL Number: BOL-2026-002", "bill_of_lading_number"),
]

print("\n========== ALIAS TEST RESULTS ==========\n")

for doc_type, sample, field in tests:
    try:
        output = extract_document_fields(doc_type, sample)
        actual = output[field]["value"]

        status = "PASS" if actual else "FAIL"

        print(f"{status} | {field}")
        print(f"Input: {sample}")
        print(f"Extracted: {actual}")
        print("-" * 45)

    except Exception as e:
        print(f"ERROR | {field} | {e}")

