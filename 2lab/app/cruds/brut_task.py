from sqlalchemy.orm import Session
from app.models.brut_task import BrutTask

def create_brut_task(db: Session, task_id: str):
    task = BrutTask(task_id=task_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_brut_task(db: Session, task: BrutTask, status: str, progress: int, result: str = None):
    task.status = status
    task.progress = progress
    task.result = result
    db.commit()
    db.refresh(task)
    return task

def get_brut_task(db: Session, task_id: str):
    return db.query(BrutTask).filter(BrutTask.task_id == task_id).first()
