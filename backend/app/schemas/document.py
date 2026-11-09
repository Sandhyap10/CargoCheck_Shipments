from pydantic import BaseModel
from datetime import datetime


class DocumentResponse(BaseModel):
    id: int
    shipment_id: int
    document_type: str
    original_filename: str
    processing_status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True