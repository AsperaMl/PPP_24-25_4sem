from sqlalchemy import Column, Integer, String
from app.db.database import Base

class BrutTask(Base):
    __tablename__ = "brut_tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String, unique=True, index=True)  
    status = Column(String, default="running")        
    progress = Column(Integer, default=0)
    result = Column(String, nullable=True)             