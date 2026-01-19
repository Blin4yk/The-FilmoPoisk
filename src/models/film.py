from pydantic import UUID4, BaseModel


class Genre(BaseModel):
    uuid: UUID4
    name: str


class Person(BaseModel):
    uuid: UUID4
    full_name: str


class FilmShort(BaseModel):
    uuid: UUID4
    title: str
    imdb_rating: float | None = None


class FilmDetail(FilmShort):
    description: str | None = None
    genre: list[Genre] = []
    actors: list[Person] = []
    writers: list[Person] = []
    directors: list[Person] = []


class Film(BaseModel):
    id: str
    title: str
    description: str
