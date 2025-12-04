from fastapi import Query


class PaginationParams:
    """Класс-зависимость для параметров пагинации и сортировки"""
    def __init__(
        self,
        sort: str = Query("-imdb_rating", description="Сортировка по убыванию"),
        page: int = Query(1, ge=1, description="Номер страницы"),
        size: int = Query(50, ge=1, le=100, description="Размер страницы"),
    ):
        self.sort = sort
        self.page = page
        self.size = size


class FilmSearchParams(PaginationParams):
    """Класс-зависимость для параметров поиска фильмов"""
    def __init__(
        self,
        query: str = Query(..., min_length=1, description="Поисковой запрос"),
        **kwargs
    ):
        super().__init__(**kwargs)
        self.query = query


class FilmListParams(PaginationParams):
    """Класс-зависимость для параметров списка фильмов"""
    def __init__(
        self,
        genre: str | None = Query(None, description="Фильтр по жанру"),
        **kwargs
    ):
        super().__init__(**kwargs)
        self.genre = genre