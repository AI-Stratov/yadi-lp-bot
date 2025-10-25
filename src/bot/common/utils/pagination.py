"""Утилиты для пагинации."""

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    """Результат пагинации."""

    items: list[T]
    page: int
    total_pages: int
    total_items: int
    page_size: int
    start_index: int
    end_index: int

    @property
    def has_prev(self) -> bool:
        """Есть ли предыдущая страница."""
        return self.page > 0

    @property
    def has_next(self) -> bool:
        """Есть ли следующая страница."""
        return self.page < self.total_pages - 1


def paginate(items: list[T], page: int, page_size: int) -> Page[T]:
    """
    Разбить список на страницы.

    :param items: Список элементов для пагинации
    :param page: Номер страницы (начиная с 0)
    :param page_size: Размер страницы

    :return: Page: Объект с результатами пагинации
    """
    total = len(items)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))

    start = page * page_size
    end = min(start + page_size, total)

    return Page(
        items=items[start:end],
        page=page,
        total_pages=total_pages,
        total_items=total,
        page_size=page_size,
        start_index=start,
        end_index=end,
    )
