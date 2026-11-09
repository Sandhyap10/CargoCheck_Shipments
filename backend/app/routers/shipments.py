
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import Shipment
from app.schemas.shipment import ShipmentCreate, ShipmentResponse

router = APIRouter(
    prefix="/shipments",
    tags=["Shipments"]
)


# Create a shipment
@router.post("/", response_model=ShipmentResponse)
def create_shipment(
    shipment: ShipmentCreate,
    db: Session = Depends(get_db)
):
    # Check whether the Shipment ID already exists
    existing = db.query(Shipment).filter(
        Shipment.shipment_id == shipment.shipment_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Shipment ID already exists"
        )

    new_shipment = Shipment(**shipment.model_dump())

    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)

    return new_shipment


# Get all shipments
@router.get("/", response_model=list[ShipmentResponse])
def get_shipments(db: Session = Depends(get_db)):
    return db.query(Shipment).order_by(
        Shipment.created_at.desc()
    ).all()


# Get shipment by database ID
@router.get("/{shipment_db_id}", response_model=ShipmentResponse)
def get_shipment(
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

    return shipment
