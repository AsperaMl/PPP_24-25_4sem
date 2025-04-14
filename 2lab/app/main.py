from fastapi import FastAPI
from app.api import users, brut

app = FastAPI()

app.include_router(users.router, prefix="/api")
app.include_router(brut.router, prefix="/api")

# При необходимости можно добавить middleware, обработку ошибок и т.д.
