
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float,
    DateTime, ForeignKey, Boolean, JSON
)

from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False, default="executive")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Shipment(Base):
    __tablename__ = "shipments"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(String(50), unique=True, nullable=False, index=True)
    importer_name = Column(String(200))
    supplier_name = Column(String(200))
    shipment_date = Column(DateTime)
    status = Column(String(50), default="pending")
    assigned_user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)



class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(
        Integer,
        ForeignKey("shipments.id"),
        nullable=False
    )
    document_type = Column(String(50), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    processing_status = Column(String(50), default="uploaded")

    # Document version management
    is_active = Column(Boolean, default=True, nullable=False)
    replaced_at = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)



class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    field_name = Column(String(150), nullable=False)
    extracted_value = Column(Text)
    confidence_score = Column(Float)
    source_page = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class ValidationResult(Base):
    __tablename__ = "validation_results"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    field_name = Column(String(150), nullable=False)
    severity = Column(String(30), default="warning")
    status = Column(String(30), default="open")
    message = Column(Text)
    compared_values = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    extracted_field_id = Column(Integer, ForeignKey("extracted_fields.id"))
    old_value = Column(Text)
    corrected_value = Column(Text)
    corrected_by = Column(Integer, ForeignKey("users.id"))
    correction_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True)
    shipment_id = Column(Integer, ForeignKey("shipments.id"), nullable=False)
    manager_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    decision = Column(String(30), nullable=False)
    comments = Column(Text)
    approved_at = Column(DateTime, default=datetime.utcnow)
