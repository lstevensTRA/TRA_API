from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, ForeignKey, Enum, BigInteger, JSON, Boolean
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# Import Base from db module
from app.db import Base

# SQLAlchemy Models

class UploadBatch(Base):
    __tablename__ = 'upload_batches'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    method = Column(String, nullable=False)  # 'url' or 'file'
    description = Column(Text)
    status = Column(String, nullable=False, default='pending')
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    documents = relationship('Document', back_populates='upload_batch')

class FormType(Base):
    __tablename__ = 'form_types'
    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)  # 'W-2', '1099-MISC', etc.
    description = Column(Text)
    priority = Column(Integer, default=1)

    extractions = relationship('Extraction', back_populates='form_type')
    training_runs = relationship('TrainingRun', back_populates='form_type')
    training_targets = relationship('TrainingTarget', back_populates='form_type')

class Document(Base):
    __tablename__ = 'documents'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_url = Column(Text)
    filename = Column(Text)
    upload_batch_id = Column(UUID(as_uuid=True), ForeignKey('upload_batches.id'))
    status = Column(String, nullable=False, default='pending')
    error_message = Column(Text)
    file_size = Column(BigInteger)
    raw_text = Column(Text)
    processing_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    upload_batch = relationship('UploadBatch', back_populates='documents')
    extractions = relationship('Extraction', back_populates='document')

class Extraction(Base):
    __tablename__ = 'extractions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    form_type_id = Column(Integer, ForeignKey('form_types.id'), nullable=False)
    extraction_method = Column(String, nullable=False)  # 'regex', 'ml'
    fields = Column(JSON, nullable=False)
    confidence = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    document = relationship('Document', back_populates='extractions')
    form_type = relationship('FormType', back_populates='extractions')
    annotations = relationship('Annotation', back_populates='extraction')

class Annotation(Base):
    __tablename__ = 'annotations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extraction_id = Column(UUID(as_uuid=True), ForeignKey('extractions.id'), nullable=False)
    annotator_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    corrected_fields = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default='pending')
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    extraction = relationship('Extraction', back_populates='annotations')
    annotator = relationship('User', back_populates='annotations')

class TrainingRun(Base):
    __tablename__ = 'training_runs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    form_type_id = Column(Integer, ForeignKey('form_types.id'), nullable=False)
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True))
    status = Column(String, nullable=False, default='started')
    accuracy = Column(Float)
    regex_baseline = Column(Float)
    model_file_path = Column(Text)
    notes = Column(Text)

    form_type = relationship('FormType', back_populates='training_runs')

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    annotations = relationship('Annotation', back_populates='annotator')

class TrainingTarget(Base):
    __tablename__ = 'training_targets'
    id = Column(Integer, primary_key=True, autoincrement=True)
    form_type_id = Column(Integer, ForeignKey('form_types.id'))
    target_count = Column(Integer, nullable=False, default=100)
    priority = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    form_type = relationship('FormType', back_populates='training_targets')

# Pydantic Models for FastAPI

# --- Batch Upload ---
class BatchUploadRequest(BaseModel):
    method: str = Field(..., description="'url' or 'file'")
    urls: Optional[List[str]] = Field(None, description="List of URLs to import")
    files: Optional[List[str]] = Field(None, description="List of file names (for uploads)")
    description: Optional[str] = None

class BatchUploadResponse(BaseModel):
    batch_id: str
    status: str
    total_documents: int
    created_at: datetime

# --- Document ---
class DocumentResponse(BaseModel):
    id: str
    source_url: Optional[str]
    filename: Optional[str]
    upload_batch_id: Optional[str]
    status: str
    error_message: Optional[str]
    file_size: Optional[int]
    raw_text: Optional[str]
    processing_time_ms: Optional[int]
    created_at: datetime
    updated_at: datetime

# --- Extraction ---
class ExtractionResponse(BaseModel):
    id: str
    document_id: str
    form_type_id: int
    extraction_method: str
    fields: Dict[str, Any]
    confidence: Optional[float]
    created_at: datetime

# --- Annotation ---
class AnnotationRequest(BaseModel):
    extraction_id: str
    annotator_id: Optional[str]
    corrected_fields: Dict[str, Any]
    status: str
    notes: Optional[str]

class AnnotationResponse(BaseModel):
    id: str
    extraction_id: str
    annotator_id: Optional[str]
    corrected_fields: Dict[str, Any]
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

# --- Training Progress ---
class TrainingProgressItem(BaseModel):
    form_type: str
    description: Optional[str]
    annotated_count: int
    total_extractions: int
    completion_percentage: Optional[float]
    avg_confidence: Optional[float]

class TrainingProgressResponse(BaseModel):
    progress: List[TrainingProgressItem]

# --- Training Run ---
class TrainingRunRequest(BaseModel):
    form_type_id: int
    notes: Optional[str]

class TrainingRunResponse(BaseModel):
    id: str
    form_type_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    accuracy: Optional[float]
    regex_baseline: Optional[float]
    model_file_path: Optional[str]
    notes: Optional[str] 