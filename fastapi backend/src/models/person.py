from pydantic import BaseModel
from pydantic.types import UUID4


class Person(BaseModel):
    id: UUID4
    name: str
