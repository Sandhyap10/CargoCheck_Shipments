
from pydantic import BaseModel, validator
from datetime import date
from typing import Optional
import re


class ShipmentCreate(BaseModel):
    shipment_id: str
    importer_name: str
    supplier_name: str
    shipment_date: Optional[date] = None
    status: str = "Pending"

    @validator("shipment_id")
    def validate_shipment_id(cls, value):
        value = value.strip()

        if not re.fullmatch(r"SHP-\d{3}", value):
            raise ValueError(
                "Shipment ID must follow the format SHP-001 "
                "(SHP- followed by exactly 3 digits)"
            )

        return value


class ShipmentResponse(BaseModel):
    id: int
    shipment_id: str
    importer_name: str
    supplier_name: str
    shipment_date: Optional[date] = None
    status: str

    class Config:
        from_attributes = True
