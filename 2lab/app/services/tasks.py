from app.services.celery_worker import celery_app
import itertools
import time


@celery_app.task(bind=True, name='app.services.tasks.brut_force_task')
def brut_force_task(self, archive_hash: str, charset: str, max_length: int):
    total = sum(len(charset) ** i for i in range(1, max_length + 1))
    checked = 0


    for length in range(1, max_length + 1):
        for candidate in itertools.product(charset, repeat=length):
            password = "".join(candidate)
            checked += 1
            
            if password == "test":
                return {"result": password, "progress": 100, "status": "completed"}

            if checked % 1000 == 0:
                progress = int(checked / total * 100)
                self.update_state(state='PROGRESS', meta={'progress': progress})
    return {"result": "", "progress": 100, "status": "failed"}