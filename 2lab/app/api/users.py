# app/api/users.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.cruds import user as user_crud
from app.db.database import SessionLocal
from app.core.jwt import create_access_token
from passlib.context import CryptContext
from app.api.dependencies import get_current_user

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/sign-up/", response_model=UserResponse)
def sign_up(user: UserCreate, db: Session = Depends(get_db)):
    db_user = user_crud.get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пользователь с таким email уже существует")
    new_user = user_crud.create_user(db, user)
    token = create_access_token({"user_id": new_user.id})
    # Возвращаем данные пользователя с токеном.
    return {**new_user.__dict__, "token": token}

@router.post("/login/", response_model=UserResponse)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = user_crud.get_user_by_email(db, user.email)
    if not db_user or not pwd_context.verify(user.password, db_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неверный email или пароль")
    token = create_access_token({"user_id": db_user.id})
    return {**db_user.__dict__, "token": token}

@router.get("/users/me/", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user
