
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

import csv
import io
import json

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from app.database import get_db
from app.models.entities import (
    Shipment,
    Document,
    ExtractedField,
    ValidationResult,
    Correction,
)

from app.services.validation_service import validate_shipment
from app.services.report_service import generate_shipment_report


router = APIRouter(tags=["Document Review"])


class CorrectionRequest(BaseModel):
    corrected_value: str
    correction_reason: str


# --------------------------------------------------
# GET: Retrieve active shipment documents and review results
# --------------------------------------------------

@router.get("/shipments/{shipment_db_id}/review")
def get_shipment_review(
    shipment_db_id: int,
    db: Session = Depends(get_db),
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    # Retrieve only active documents
    documents = db.query(Document).filter(
        Document.shipment_id == shipment_db_id,
        Document.is_active.is_(True)
    ).order_by(
        Document.uploaded_at.desc(),
        Document.id.desc()
    ).all()

    document_results = []

    for document in documents:

        fields = db.query(ExtractedField).filter(
            ExtractedField.document_id == document.id
        ).all()

        document_results.append({
            "document_id": document.id,
            "document_type": document.document_type,
            "filename": document.original_filename,
            "processing_status": document.processing_status,
            "is_active": document.is_active,
            "fields": [
                {
                    "id": field.id,
                    "field_name": field.field_name,
                    "extracted_value": field.extracted_value,
                    "confidence_score": field.confidence_score,
                    "source_page": field.source_page,
                }
                for field in fields
            ],
        })

    validations = db.query(ValidationResult).filter(
        ValidationResult.shipment_id == shipment_db_id
    ).all()

    return {
        "shipment_id": shipment.shipment_id,
        "documents": document_results,
        "validation_results": [
            {
                "id": result.id,
                "field_name": result.field_name,
                "severity": result.severity,
                "status": result.status,
                "message": result.message,
                "compared_values": result.compared_values,
            }
            for result in validations
        ],
    }


# --------------------------------------------------
# POST: Correct an extracted field and revalidate
# --------------------------------------------------

@router.post("/extracted-fields/{field_id}/corrections")
def correct_extracted_field(
    field_id: int,
    request: CorrectionRequest,
    db: Session = Depends(get_db),
):
    # 1. Find extracted field
    field = db.query(ExtractedField).filter(
        ExtractedField.id == field_id
    ).first()

    if not field:
        raise HTTPException(
            status_code=404,
            detail="Extracted field not found"
        )

    # 2. Find document containing this field
    document = db.query(Document).filter(
        Document.id == field.document_id
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    # Do not allow corrections to replaced documents
    if not document.is_active:
        raise HTTPException(
            status_code=400,
            detail="This document has been replaced. Please correct the active document instead."
        )

    shipment_db_id = document.shipment_id
    old_value = field.extracted_value

    try:
        # 3. Save correction history
        correction = Correction(
            extracted_field_id=field.id,
            old_value=old_value,
            corrected_value=request.corrected_value,
            correction_reason=request.correction_reason,
        )

        db.add(correction)

        # 4. Update extracted field
        field.extracted_value = request.corrected_value

        # 5. Retrieve active and processed documents
        shipment_documents = db.query(Document).filter(
            Document.shipment_id == shipment_db_id,
            Document.is_active.is_(True),
            Document.processing_status == "processed"
        ).order_by(
            Document.id.desc()
        ).all()

        documents_for_validation = {}

        for shipment_document in shipment_documents:

            extracted_fields = db.query(ExtractedField).filter(
                ExtractedField.document_id == shipment_document.id
            ).all()

            field_values = {
                extracted.field_name: extracted.extracted_value
                for extracted in extracted_fields
            }

            documents_for_validation[
                shipment_document.document_type
            ] = field_values

        # 6. Run validation using active documents
        new_validation_results = validate_shipment(
            documents_for_validation
        )

        # 7. Delete previous validation results
        db.query(ValidationResult).filter(
            ValidationResult.shipment_id == shipment_db_id
        ).delete(synchronize_session=False)

        # 8. Insert fresh validation results
        for result in new_validation_results:

            validation_record = ValidationResult(
                shipment_id=shipment_db_id,
                field_name=result["field_name"],
                severity=result["severity"],
                status=result["status"],
                message=result["message"],
                compared_values=result["compared_values"],
            )

            db.add(validation_record)

        # 9. Find shipment
        shipment = db.query(Shipment).filter(
            Shipment.id == shipment_db_id
        ).first()

        if not shipment:
            raise HTTPException(
                status_code=404,
                detail="Shipment not found"
            )

        # 10. Check whether all three required documents are processed
        required_document_types = {
            "Commercial Invoice",
            "Packing List",
            "Bill of Lading"
        }

        processed_document_types = {
            doc.document_type
            for doc in shipment_documents
        }

        all_documents_processed = required_document_types.issubset(
            processed_document_types
        )

        # 11. Update shipment status
        has_mismatch = any(
            result["status"] == "MISMATCH"
            for result in new_validation_results
        )

        if not all_documents_processed:
            shipment.status = "Pending"

        elif has_mismatch:
            shipment.status = "Attention Required"

        else:
            shipment.status = "Completed"

        # 12. Save correction, validation and status together
        db.commit()

        db.refresh(field)
        db.refresh(shipment)

        return {
            "message": "Correction saved and validation updated successfully",
            "field_id": field.id,
            "old_value": old_value,
            "corrected_value": field.extracted_value,
            "shipment_status": shipment.status,
            "validation_results": new_validation_results,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Unable to save correction and update validation: {str(error)}"
        )


# --------------------------------------------------
# GET: Retrieve correction history for a shipment
# --------------------------------------------------

@router.get("/shipments/{shipment_db_id}/correction-history")
def get_correction_history(
    shipment_db_id: int,
    db: Session = Depends(get_db),
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    history = (
        db.query(Correction, ExtractedField, Document)
        .join(
            ExtractedField,
            Correction.extracted_field_id == ExtractedField.id
        )
        .join(
            Document,
            ExtractedField.document_id == Document.id
        )
        .filter(
            Document.shipment_id == shipment_db_id
        )
        .order_by(Correction.created_at.desc())
        .all()
    )

    return {
        "shipment_id": shipment.shipment_id,
        "total_corrections": len(history),
        "correction_history": [
            {
                "correction_id": correction.id,
                "document_name": document.original_filename,
                "document_type": document.document_type,
                "field_name": field.field_name,
                "old_value": correction.old_value,
                "corrected_value": correction.corrected_value,
                "correction_reason": correction.correction_reason,
                "corrected_at": correction.created_at,
            }
            for correction, field, document in history
        ],
    }


# --------------------------------------------------
# GET: Export shipment data as CSV
# --------------------------------------------------

@router.get("/shipments/{shipment_db_id}/export")
def export_shipment_csv(
    shipment_db_id: int,
    db: Session = Depends(get_db)
):
    shipment = (
        db.query(Shipment)
        .filter(Shipment.id == shipment_db_id)
        .first()
    )

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    documents = (
        db.query(Document)
        .filter(
            Document.shipment_id == shipment_db_id,
            Document.is_active.is_(True),
            Document.processing_status == "processed"
        )
        .all()
    )

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No processed documents available for export."
        )

    document_types = [
        "Commercial Invoice",
        "Packing List",
        "Bill of Lading"
    ]

    available_types = {
        doc.document_type for doc in documents
    }

    if not all(
        doc_type in available_types
        for doc_type in document_types
    ):
        raise HTTPException(
            status_code=400,
            detail="All three document types must be processed before export."
        )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Shipment ID",
        "Document Type",
        "Field Name",
        "Verified Value",
        "Confidence Score"
    ])

    for document in documents:

        fields = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.document_id == document.id
            )
            .order_by(ExtractedField.field_name)
            .all()
        )

        for field in fields:
            writer.writerow([
                shipment.shipment_id,
                document.document_type,
                field.field_name,
                field.extracted_value or "",
                field.confidence_score or 0
            ])

    output.seek(0)

    filename = f"CargoCheck_{shipment.shipment_id}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


# --------------------------------------------------
# GET: Retrieve shipment accuracy report
# --------------------------------------------------

@router.get("/shipments/{shipment_db_id}/report")
def get_shipment_report(
    shipment_db_id: int,
    db: Session = Depends(get_db)
):
    report = generate_shipment_report(
        shipment_db_id,
        db
    )

    if report is None:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    return report


# --------------------------------------------------
# GET: Export shipment data as Excel workbook
# --------------------------------------------------

@router.get("/shipments/{shipment_db_id}/export/excel")
def export_shipment_excel(
    shipment_db_id: int,
    db: Session = Depends(get_db)
):
    # 1. Find shipment
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    # 2. Retrieve active and processed documents only
    documents = db.query(Document).filter(
        Document.shipment_id == shipment_db_id,
        Document.is_active.is_(True),
        Document.processing_status == "processed"
    ).all()

    if not documents:
        raise HTTPException(
            status_code=400,
            detail="No processed documents available for export."
        )

    # 3. Check that all three document types are available
    document_types = [
        "Commercial Invoice",
        "Packing List",
        "Bill of Lading"
    ]

    documents_by_type = {
        document.document_type: document
        for document in documents
    }

    if not all(
        doc_type in documents_by_type
        for doc_type in document_types
    ):
        raise HTTPException(
            status_code=400,
            detail="All three document types must be processed before export."
        )

    # 4. Create Excel workbook
    workbook = Workbook()

    # Remove default worksheet
    default_sheet = workbook.active
    workbook.remove(default_sheet)

    # Common header styling
    header_fill = PatternFill(
        start_color="1F4E78",
        end_color="1F4E78",
        fill_type="solid"
    )

    header_font = Font(
        bold=True,
        color="FFFFFF"
    )

    # 5. Create one sheet for each document type
    for document_type in document_types:

        document = documents_by_type[document_type]

        sheet = workbook.create_sheet(
            title=document_type
        )

        # Shipment information
        sheet.append(["Shipment ID", shipment.shipment_id])
        sheet.append(["Document Name", document.original_filename])
        sheet.append([])

        # Column headers
        headers = [
            "Field Name",
            "Verified Value",
            "Confidence Score",
            "Source Page"
        ]

        sheet.append(headers)

        fields = db.query(ExtractedField).filter(
            ExtractedField.document_id == document.id
        ).order_by(
            ExtractedField.field_name
        ).all()

        for field in fields:
            sheet.append([
                field.field_name,
                field.extracted_value or "",
                field.confidence_score or 0,
                field.source_page or ""
            ])

        # Style column headers
        for cell in sheet[4]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(
                horizontal="center"
            )

        # Adjust column widths
        sheet.column_dimensions["A"].width = 28
        sheet.column_dimensions["B"].width = 35
        sheet.column_dimensions["C"].width = 20
        sheet.column_dimensions["D"].width = 15

        sheet.freeze_panes = "A5"
        sheet.auto_filter.ref = f"A4:D{sheet.max_row}"

    # 6. Create Validation Summary sheet
    validation_sheet = workbook.create_sheet(
        title="Validation Summary"
    )

    validation_sheet.append([
        "Shipment ID",
        shipment.shipment_id
    ])

    validation_sheet.append([])

    validation_headers = [
        "Field Name",
        "Severity",
        "Status",
        "Message",
        "Compared Values"
    ]

    validation_sheet.append(validation_headers)

    validation_results = db.query(ValidationResult).filter(
        ValidationResult.shipment_id == shipment_db_id
    ).all()

    for result in validation_results:

        compared_values = result.compared_values

        if isinstance(compared_values, (dict, list)):
            compared_values = json.dumps(
                compared_values,
                ensure_ascii=False
            )

        validation_sheet.append([
            result.field_name,
            result.severity,
            result.status,
            result.message,
            compared_values or ""
        ])

    # Style validation headers
    for cell in validation_sheet[3]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(
            horizontal="center"
        )

    validation_sheet.column_dimensions["A"].width = 25
    validation_sheet.column_dimensions["B"].width = 15
    validation_sheet.column_dimensions["C"].width = 18
    validation_sheet.column_dimensions["D"].width = 55
    validation_sheet.column_dimensions["E"].width = 45

    validation_sheet.freeze_panes = "A4"
    validation_sheet.auto_filter.ref = (
        f"A3:E{validation_sheet.max_row}"
    )

    # 7. Save workbook to memory
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # 8. Return downloadable Excel file
    filename = f"CargoCheck_{shipment.shipment_id}.xlsx"

    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        }
    )
