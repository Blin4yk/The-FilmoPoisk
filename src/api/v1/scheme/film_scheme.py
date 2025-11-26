from pydantic import BaseModel, UUID4

class Genre(BaseModel):
    name: str

class Person(BaseModel):
    id: str
    full_name: str

class FilmShort(BaseModel):
    id: str
    title: str
    imdb_rating: float | None = None

class FilmDetail(FilmShort):
    description: str | None = None
    genres: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []