# Label Studio Integration for Tax Form ML Training Pipeline

This directory contains scripts and configuration for integrating Label Studio with your tax form ML training workflow.

## Setup
1. Install dependencies:
   ```sh
   pip install -r ../requirements.txt
   ```
2. Set environment variables in a `.env` file or your shell:
   - `SUPABASE_URL`, `SUPABASE_KEY`
   - `LABEL_STUDIO_URL`, `LABEL_STUDIO_API_KEY`
3. Start Label Studio:
   ```sh
   label-studio start
   ```
4. Create a new project in Label Studio and import the labeling config from `labelstudio_taxform_template.xml`.

## Scripts

### 1. Export to Label Studio
Export documents and extractions from Supabase to Label Studio format:
```sh
python export_to_labelstudio.py --output tasks.json
```
To push tasks directly to a Label Studio project:
```sh
python export_to_labelstudio.py --push --ls_project <project_id>
```

### 2. Import from Label Studio
Import completed annotations from Label Studio back to Supabase:
```sh
python import_from_labelstudio.py --ls_project <project_id>
```

### 3. Sync Training Data
Sync both ways (export new docs/extractions, import new annotations):
```sh
python sync_training_data.py --ls_project <project_id>
```

## Labeling Template
- Use `labelstudio_taxform_template.xml` as the labeling config in your Label Studio project.
- Fields: Income, SSN, FilingStatus, Other (for generic extraction).

## Notes
- All scripts use environment variables for credentials.
- Batch operations are supported for efficiency.
- Error handling and logging are included for robust automation.

## Workflow
1. Export or sync data to Label Studio for annotation.
2. Annotators label fields in the Label Studio UI.
3. Import or sync completed annotations back to Supabase.
4. Use annotated data for ML training and evaluation. 