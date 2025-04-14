import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.brut import BrutRequest, BrutResponse, BrutStatusResponse
from app.cruds import brut_task as brut_crud
from app.db.database import SessionLocal
from app.services.celery_worker import celery_app

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/brut_hash", response_model=BrutResponse)
def start_brut(request: BrutRequest, db: Session = Depends(get_db)):
    if request.max_length > 8:
        raise HTTPException(status_code=400, detail="Максимальная длина не должна превышать 8")

    task_uuid = str(uuid.uuid4())
    # Создаем запись задачи в БД
    brut_crud.create_brut_task(db, task_uuid)
    # Запускаем задачу через Celery
    celery_app.send_task('app.services.tasks.brut_force_task', args=[request.hash, request.charset, request.max_length], task_id=task_uuid)
    return BrutResponse(task_id=task_uuid)


@router.get("/get_status", response_model=BrutStatusResponse)
def get_status(task_id: str, db: Session = Depends(get_db)):
    try:
        task_record = brut_crud.get_brut_task(db, task_id)
        if not task_record:
            raise HTTPException(status_code=404, detail="Задача не найдена")

        from celery.result import AsyncResult
        res = AsyncResult(task_id, app=celery_app)

        # Значения по умолчанию
        status = "pending"
        progress = task_record.progress or 0
        result = task_record.result or ""  

        if res.state == "PENDING":
            status = "pending"
        elif res.state == "PROGRESS":
            if res.info:
                progress = res.info.get("progress", progress)
            status = "running"
        elif res.state == "SUCCESS":
            if res.result:
                meta = res.result
                progress = meta.get("progress", 100)
                status = meta.get("status", "completed")
                result = meta.get("result", "")  
            else:
                status = "completed"
                progress = 100
            
           
            if result is None:
                result = ""
                
            brut_crud.update_brut_task(db, task_record, status, progress, result)
        elif res.state == "FAILURE":
            status = "failed"
            # Используем пустую строку вместо None
            brut_crud.update_brut_task(db, task_record, status, progress, "")
        
     
        if result is None:
            result = ""
            
        return BrutStatusResponse(status=status, progress=progress, result=result)
    
    except Exception as e:
        # Добавляем обработку любых исключений для диагностики
        print(f"Ошибка при получении статуса задачи: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при получении статуса: {str(e)}")