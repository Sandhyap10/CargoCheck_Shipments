
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Shipment, Document
from app.schemas.document import DocumentResponse


router = APIRouter(
    prefix="/shipments",
    tags=["Documents"]
)

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "uploads"

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

ALLOWED_DOCUMENT_TYPES = {
    "Commercial Invoice",
    "Packing List",
    "Bill of Lading"
}

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.get(
    "/{shipment_db_id}/documents",
    response_model=list[DocumentResponse]
)
def get_shipment_documents(
    shipment_db_id: int,
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    # Return only currently active documents
    documents = db.query(Document).filter(
        Document.shipment_id == shipment_db_id,
        Document.is_active.is_(True)
    ).order_by(
        Document.uploaded_at.asc(),
        Document.id.asc()
    ).all()

    return documents


@router.post(
    "/{shipment_db_id}/documents",
    response_model=DocumentResponse
)
async def upload_document(
    shipment_db_id: int,
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. Check whether shipment exists
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    # 2. Validate document type
    if document_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid document type"
        )

    # 3. Validate file extension
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only PDF, JPG and PNG files are allowed"
        )

    # 4. Read and validate file size
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File size must not exceed 10 MB"
        )

    # 5. Create shipment-specific upload directory
    shipment_dir = UPLOAD_DIR / str(shipment_db_id)
    shipment_dir.mkdir(parents=True, exist_ok=True)

    # 6. Generate unique filename
    saved_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = shipment_dir / saved_filename

    try:
        # 7. Save new file
        file_path.write_bytes(content)

        # 8. Find currently active document of this type
        old_documents = db.query(Document).filter(
            Document.shipment_id == shipment_db_id,
            Document.document_type == document_type,
            Document.is_active.is_(True)
        ).all()

        # 9. Mark previous versions inactive
        for old_document in old_documents:
            old_document.is_active = False
            old_document.replaced_at = datetime.utcnow()

        # 10. Create new active document
        new_document = Document(
            shipment_id=shipment_db_id,
            document_type=document_type,
            original_filename=original_filename,
            file_path=str(file_path),
            processing_status="Uploaded",
            is_active=True,
            replaced_at=None
        )

        db.add(new_document)

        # 11. Save database transaction
        db.commit()
        db.refresh(new_document)

        return new_document

    except Exception:
        db.rollback()

        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Could not save the document"
        )

    finally:
        await file.close()


# NEW: Preview original uploaded document
@router.get(
    "/{shipment_db_id}/documents/{document_id}/preview"
)
def preview_document(
    shipment_db_id: int,
    document_id: int,
    db: Session = Depends(get_db)
):
    # 1. Verify shipment exists
    shipment = db.query(Shipment).filter(
        Shipment.id == shipment_db_id
    ).first()

    if not shipment:
        raise HTTPException(
            status_code=404,
            detail="Shipment not found"
        )

    # 2. Find active document belonging to this shipment
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.shipment_id == shipment_db_id,
        Document.is_active.is_(True)
    ).first()

    if not document:
        raise HTTPException(
            status_code=404,
            detail="Active document not found"
        )

    # 3. Resolve and validate file location
    file_path = Path(document.file_path).resolve()

    shipment_directory = (
        UPLOAD_DIR / str(shipment_db_id)
    ).resolve()

    if not file_path.is_relative_to(shipment_directory):
        raise HTTPException(
            status_code=403,
            detail="Invalid document file location"
        )

    # 4. Check whether file exists
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Original document file not found"
        )

    # 5. Validate extension
    extension = file_path.suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document format"
        )

    # 6. Determine content type
    media_type = mimetypes.guess_type(
        file_path.name
    )[0]

    if media_type not in {
        "application/pdf",
        "image/jpeg",
        "image/png"
    }:
        raise HTTPException(
            status_code=400,
            detail="Unsupported document content type"
        )

    # 7. Return file for inline browser preview
    return FileResponse(
        path=file_path,
        media_type=media_type,
        headers={
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff"
        }
    )
