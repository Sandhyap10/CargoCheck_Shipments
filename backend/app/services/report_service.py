
from sqlalchemy.orm import Session

from app.models.entities import (
    Shipment,
    Document,
    ExtractedField,
    ValidationResult,
    Correction,
)


def generate_shipment_report(
    shipment_db_id: int,
    db: Session
):
    # 1. Check whether shipment exists
    shipment = (
        db.query(Shipment)
        .filter(Shipment.id == shipment_db_id)
        .first()
    )

    if not shipment:
        return None

    # 2. Get active documents that have been processed
    processed_documents = (
        db.query(Document)
        .filter(
            Document.shipment_id == shipment_db_id,
            Document.is_active.is_(True),
            Document.processing_status == "processed"
        )
        .all()
    )

    # 3. Count extracted fields from processed documents
    document_ids = [doc.id for doc in processed_documents]

    fields = []

    if document_ids:
        fields = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.document_id.in_(document_ids)
            )
            .all()
        )

    # 4. Count all correction records for this shipment.
    # This includes historical corrections on replaced documents.
    total_corrections = (
        db.query(Correction)
        .join(
            ExtractedField,
            Correction.extracted_field_id == ExtractedField.id
        )
        .join(
            Document,
            ExtractedField.document_id == Document.id
        )
        .filter(Document.shipment_id == shipment_db_id)
        .count()
    )

    # 5. Get validation results
    validation_results = (
        db.query(ValidationResult)
        .filter(
            ValidationResult.shipment_id == shipment_db_id
        )
        .all()
    )

    matched_fields = sum(
        1 for item in validation_results
        if item.status == "MATCH"
    )

    mismatched_fields = sum(
        1 for item in validation_results
        if item.status == "MISMATCH"
    )

    not_checked_fields = sum(
        1 for item in validation_results
        if item.status == "NOT_CHECKED"
    )

    # 6. Prepare report
    return {
        "shipment_id": shipment.shipment_id,
        "importer_name": shipment.importer_name,
        "supplier_name": shipment.supplier_name,
        "shipment_status": shipment.status,

        "total_documents_processed": len(processed_documents),
        "total_fields_extracted": len(fields),
        "total_manual_corrections": total_corrections,

        "matched_fields": matched_fields,
        "mismatched_fields": mismatched_fields,
        "not_checked_fields": not_checked_fields,

        "validation_summary": {
            "total_validation_results": len(validation_results),
            "matched": matched_fields,
            "mismatched": mismatched_fields,
            "not_checked": not_checked_fields,
        },
    }
