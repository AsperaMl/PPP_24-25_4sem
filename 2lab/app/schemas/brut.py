from pydantic import BaseModel

class BrutRequest(BaseModel):
    hash: str
    charset: str
    max_length: int

class BrutResponse(BaseModel):
    task_id: str

class BrutStatusResponse(BaseModel):
    status: str
    progress: int
    result: str = None
