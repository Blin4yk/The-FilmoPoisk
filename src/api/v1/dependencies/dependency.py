from fastapi import Query

class PaginationParams:
    """Базовый класс для пагинации"""
    def __init__(
        self,
        sort: str = Query("-imdb_rating", description="Sort by field (- for DESC)"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Page size")
    ):
        self.sort = sort
        self.page = page
        self.size = size
        self.skip = (page - 1) * size

