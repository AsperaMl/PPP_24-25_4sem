from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from sqlalchemy.exc import IntegrityError
import os

DATABASE_URL = "sqlite:///./app.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

from sqlalchemy import event

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON;")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Cinema(Base):
    __tablename__ = "cinemas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    movies = relationship(
        "Movie",
        back_populates="cinema",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Movie(Base):
    __tablename__ = "movies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    genre = Column(String, nullable=False)
    cinema_id = Column(Integer, ForeignKey("cinemas.id", ondelete="CASCADE"), nullable=False)
    cinema = relationship("Cinema", back_populates="movies")

Base.metadata.create_all(bind=engine)

class CinemaBase(BaseModel):
    name: str = Field(..., min_length=1)
    address: str = Field(..., min_length=1)

class CinemaCreate(CinemaBase):
    pass

class CinemaOut(CinemaBase):
    id: int
    class Config:
        orm_mode = True

class MovieBase(BaseModel):
    name: str = Field(..., min_length=1)
    genre: str = Field(..., min_length=1)

class MovieCreate(MovieBase):
    cinema_id: int

class MovieUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    genre: Optional[str] = Field(None, min_length=1)

class MovieOut(MovieBase):
    id: int
    cinema_id: int
    class Config:
        orm_mode = True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

@app.get("/cinemas", response_model=List[CinemaOut])
def list_cinemas(db: Session = Depends(get_db)):
    cinemas = db.query(Cinema).all()
    return cinemas

@app.post(
    "/cinemas",
    response_model=CinemaOut,
    status_code=status.HTTP_201_CREATED,
)
def create_cinema(cinema_in: CinemaCreate, db: Session = Depends(get_db)):
    new_cinema = Cinema(name=cinema_in.name.strip(), address=cinema_in.address.strip())
    db.add(new_cinema)
    try:
        db.commit()
        db.refresh(new_cinema)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create cinema due to integrity error",
        )
    return new_cinema

@app.get("/cinemas/{cinema_id}/movies", response_model=List[MovieOut])
def list_movies_by_cinema(cinema_id: int, db: Session = Depends(get_db)):
    cinema = db.query(Cinema).filter(Cinema.id == cinema_id).first()
    if not cinema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cinema with id={cinema_id} not found",
        )
    return cinema.movies

@app.delete("/cinemas/{cinema_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_cinema(cinema_id: int, db: Session = Depends(get_db)):
    cinema = db.query(Cinema).filter(Cinema.id == cinema_id).first()
    if not cinema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cinema with id={cinema_id} not found",
        )
    db.delete(cinema)
    db.commit()
    return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={})

@app.get("/movies", response_model=List[MovieOut])
def list_movies(
    cinema_id: Optional[int] = Query(None, description="Filter by cinema_id"),
    db: Session = Depends(get_db),
):
    query = db.query(Movie)
    if cinema_id is not None:
        cinema = db.query(Cinema).filter(Cinema.id == cinema_id).first()
        if not cinema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cinema with id={cinema_id} not found",
            )
        query = query.filter(Movie.cinema_id == cinema_id)
    movies = query.all()
    return movies

@app.post(
    "/movies",
    response_model=MovieOut,
    status_code=status.HTTP_201_CREATED,
)
def create_movie(movie_in: MovieCreate, db: Session = Depends(get_db)):
    cinema = db.query(Cinema).filter(Cinema.id == movie_in.cinema_id).first()
    if not cinema:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cinema with id={movie_in.cinema_id} not found",
        )
    new_movie = Movie(
        name=movie_in.name.strip(),
        genre=movie_in.genre.strip(),
        cinema_id=movie_in.cinema_id,
    )
    db.add(new_movie)
    try:
        db.commit()
        db.refresh(new_movie)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create movie due to integrity error",
        )
    return new_movie

@app.put("/movies/{movie_id}", response_model=MovieOut)
def update_movie(
    movie_id: int, movie_update: MovieUpdate, db: Session = Depends(get_db)
):
    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie with id={movie_id} not found",
        )
    updated = False
    if movie_update.name is not None:
        movie.name = movie_update.name.strip()
        updated = True
    if movie_update.genre is not None:
        movie.genre = movie_update.genre.strip()
        updated = True
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided for update",
        )
    try:
        db.commit()
        db.refresh(movie)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update movie due to integrity error",
        )
    return movie
