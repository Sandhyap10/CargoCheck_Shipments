
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.processing_service import process_shipment

router = APIRouter(
    prefix="/shipments",
    tags=["Shipment Processing"]
)


@router.post("/{shipment_db_id}/process")
def process_shipment_api(
    shipment_db_id: int,
    db: Session = Depends(get_db)
):
    try:
        return process_shipment(shipment_db_id, db)

    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error)
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Shipment processing failed: {str(error)}"
        )
