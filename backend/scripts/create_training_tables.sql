-- Training Workflow Tables for Supabase
-- Run this in your Supabase SQL Editor

-- Create form_types table
CREATE TABLE IF NOT EXISTS form_types (
    id SERIAL PRIMARY KEY,
    code VARCHAR UNIQUE NOT NULL,
    description TEXT,
    priority INTEGER DEFAULT 1
);

-- Create upload_batches table
CREATE TABLE IF NOT EXISTS upload_batches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    method VARCHAR NOT NULL,
    description TEXT,
    status VARCHAR NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_url TEXT,
    filename TEXT,
    upload_batch_id UUID REFERENCES upload_batches(id),
    status VARCHAR NOT NULL DEFAULT 'pending',
    error_message TEXT,
    file_size BIGINT,
    raw_text TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create extractions table
CREATE TABLE IF NOT EXISTS extractions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id),
    form_type_id INTEGER NOT NULL REFERENCES form_types(id),
    extraction_method VARCHAR NOT NULL,
    fields JSONB NOT NULL,
    confidence FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE NOT NULL,
    name VARCHAR,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create annotations table
CREATE TABLE IF NOT EXISTS annotations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    extraction_id UUID NOT NULL REFERENCES extractions(id),
    annotator_id UUID REFERENCES users(id),
    corrected_fields JSONB NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL
);

-- Create training_runs table
CREATE TABLE IF NOT EXISTS training_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_type_id INTEGER NOT NULL REFERENCES form_types(id),
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR NOT NULL DEFAULT 'started',
    accuracy FLOAT,
    regex_baseline FLOAT,
    model_file_path TEXT,
    notes TEXT
);

-- Create training_targets table
CREATE TABLE IF NOT EXISTS training_targets (
    id SERIAL PRIMARY KEY,
    form_type_id INTEGER REFERENCES form_types(id),
    target_count INTEGER NOT NULL DEFAULT 100,
    priority INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create training_progress view
CREATE OR REPLACE VIEW training_progress AS
SELECT 
    ft.code as form_type,
    ft.description,
    COUNT(DISTINCT e.id) as total_extractions,
    COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN e.id END) as annotated_count,
    CASE 
        WHEN COUNT(DISTINCT e.id) > 0 
        THEN ROUND((COUNT(DISTINCT CASE WHEN a.id IS NOT NULL THEN e.id END)::FLOAT / COUNT(DISTINCT e.id)::FLOAT) * 100, 2)
        ELSE NULL 
    END as completion_percentage,
    AVG(e.confidence) as avg_confidence
FROM form_types ft
LEFT JOIN extractions e ON ft.id = e.form_type_id
LEFT JOIN annotations a ON e.id = a.extraction_id
GROUP BY ft.id, ft.code, ft.description
ORDER BY ft.priority DESC, ft.code;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_documents_upload_batch_id ON documents(upload_batch_id);
CREATE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id);
CREATE INDEX IF NOT EXISTS idx_extractions_form_type_id ON extractions(form_type_id);
CREATE INDEX IF NOT EXISTS idx_annotations_extraction_id ON annotations(extraction_id);
CREATE INDEX IF NOT EXISTS idx_training_runs_form_type_id ON training_runs(form_type_id);
CREATE INDEX IF NOT EXISTS idx_training_targets_form_type_id ON training_targets(form_type_id); 