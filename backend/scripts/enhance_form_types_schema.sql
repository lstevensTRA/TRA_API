-- Enhance form_types table to store complete wi_patterns data
-- Run this in your Supabase SQL Editor

-- Add new columns to form_types table
ALTER TABLE form_types 
ADD COLUMN IF NOT EXISTS category VARCHAR(20),
ADD COLUMN IF NOT EXISTS form_pattern TEXT,
ADD COLUMN IF NOT EXISTS field_definitions JSONB,
ADD COLUMN IF NOT EXISTS calculation_rules JSONB,
ADD COLUMN IF NOT EXISTS identifiers JSONB;

-- Add comments for documentation
COMMENT ON COLUMN form_types.category IS 'Form category: SE, Non-SE, or Neither';
COMMENT ON COLUMN form_types.form_pattern IS 'Main detection regex pattern';
COMMENT ON COLUMN form_types.field_definitions IS 'JSON object containing field names and their regex patterns';
COMMENT ON COLUMN form_types.calculation_rules IS 'JSON object containing income/withholding calculation rules';
COMMENT ON COLUMN form_types.identifiers IS 'JSON object containing payer information patterns';

-- Create index on category for better query performance
CREATE INDEX IF NOT EXISTS idx_form_types_category ON form_types(category);

-- Verify the changes
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'form_types' 
ORDER BY ordinal_position; 