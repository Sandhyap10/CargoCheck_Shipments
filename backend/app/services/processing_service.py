
from sqlalchemy.orm import Session

from app.models.entities import (
    Shipment,
    Document,
    ExtractedField,
    ValidationResult,
    Correction,
)

from app.services.document_extractor import (
    extract_text_from_document
)

from app.services.field_extractor import (
    extract_document_fields
)

from app.services.validation_service import (
    validate_shipment
)


REQUIRED_DOCUMENT_TYPES = [
    "Commercial Invoice",
    "Packing List",
    "Bill of Lading",
]


def process_shipment(shipment_db_id: int, db: Session):

    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise ValueError("Shipment not found")

    # Retrieve only active documents
    documents = db.query(Document).filter(
        Document.shipment_id == shipment_db_id,
        Document.is_active.is_(True)
    ).order_by(
        Document.id.desc()
    ).all()

    if not documents:
        raise ValueError(
            "No active documents uploaded for this shipment"
        )

    # Check for missing document types
    active_document_types = {
        document.document_type for document in documents
    }

    missing_documents = [
        doc_type
        for doc_type in REQUIRED_DOCUMENT_TYPES
        if doc_type not in active_document_types
    ]

    if missing_documents:
        raise ValueError(
            "Missing required documents: "
            + ", ".join(missing_documents)
        )

    # Ensure only one active document per type
    if len(active_document_types) != len(documents):
        raise ValueError(
            "Multiple active documents found for the same document type. "
            "Please replace duplicate documents before processing."
        )

    extracted_documents = {}

    try:

        # Process only active documents
        for document in documents:

            text = extract_text_from_document(
                document.file_path
            )

            fields = extract_document_fields(
                document.document_type,
                text
            )

            # Retrieve existing extracted fields
            existing_fields = db.query(ExtractedField).filter(
                ExtractedField.document_id == document.id
            ).all()

            existing_fields_map = {
                field.field_name: field
                for field in existing_fields
            }

            # Store values for validation
            document_values = {}

            for field_name, field_data in fields.items():

                extracted_value = field_data["value"]

                existing_field = existing_fields_map.get(
                    field_name
                )

                if existing_field:

                    # Check whether this field has correction history
                    has_correction = db.query(Correction.id).filter(
                        Correction.extracted_field_id == existing_field.id
                    ).first()

                    if has_correction:
                        # Preserve manually corrected value
                        final_value = existing_field.extracted_value

                    else:
                        # Update previously extracted value
                        existing_field.extracted_value = extracted_value
                        existing_field.confidence_score = field_data[
                            "confidence"
                        ]
                        final_value = extracted_value

                else:
                    # Create a new extracted field
                    new_field = ExtractedField(
                        document_id=document.id,
                        field_name=field_name,
                        extracted_value=extracted_value,
                        confidence_score=field_data["confidence"]
                    )

                    db.add(new_field)
                    final_value = extracted_value

                document_values[field_name] = final_value

            extracted_documents[
                document.document_type
            ] = document_values

            document.processing_status = "processed"

        # Run validation using active documents only
        validation_results = validate_shipment(
            extracted_documents
        )

        # Replace previous validation results
        db.query(ValidationResult).filter(
            ValidationResult.shipment_id == shipment_db_id
        ).delete(synchronize_session=False)

        # Save updated validation results
        for result in validation_results:

            validation = ValidationResult(
                shipment_id=shipment_db_id,
                field_name=result["field_name"],
                severity=result["severity"],
                status=result["status"],
                message=result["message"],
                compared_values=result["compared_values"]
            )

            db.add(validation)

        # NEW: Update shipment status based on validation
        has_mismatch = any(
            result["status"] == "MISMATCH"
            for result in validation_results
        )

        if has_mismatch:
            shipment.status = "Attention Required"
        else:
            shipment.status = "Completed"

        # Save extracted fields, validation and shipment status
        db.commit()

        return {
            "shipment_id": shipment.shipment_id,
            "shipment_status": shipment.status,
            "documents_processed": len(documents),
            "fields_extracted": sum(
                len(fields)
                for fields in extracted_documents.values()
            ),
            "validation_results": validation_results
        }

    except Exception:
        db.rollback()
        raise
