import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models import FormType, TrainingTarget
from app.db import SessionLocal

# Import form_patterns from wi_patterns.py
from app.utils.wi_patterns import form_patterns

def main():
    db = SessionLocal()
    for code, pattern in form_patterns.items():
        description = pattern.get('pattern', code)
        # Insert form type if not exists
        form_type = db.query(FormType).filter_by(code=code).first()
        if not form_type:
            form_type = FormType(code=code, description=description)
            db.add(form_type)
            db.commit()
            db.refresh(form_type)
        # Insert training target if not exists
        target = db.query(TrainingTarget).filter_by(form_type_id=form_type.id).first()
        if not target:
            target = TrainingTarget(form_type_id=form_type.id, target_count=100)
            db.add(target)
    db.commit()
    db.close()
    print('Form types and training targets initialized.')

if __name__ == '__main__':
    main() 