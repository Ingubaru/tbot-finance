from typing import List, NamedTuple


import config
import db


class Category(NamedTuple):
    name: str
    monthly_limit: int


def set_category_limit(name: str, limit: int) -> None:
    cursor = db.get_cursor()
    cursor.execute(f'UPDATE categories '
                   f'SET monthly_limit={limit} '
                   f'WHERE name="{name.capitalize()}"')


def get_category(name: str) -> Category | None:
    cursor = db.get_cursor()
    cursor.execute(f'SELECT name, monthly_limit '
                   f'FROM categories '
                   f'WHERE name="{name}"')
    row = cursor.fetchone()
    if not row:
        return None
    result = Category(name=row[0], monthly_limit=row[1])
    return result


def get_categories() -> List[Category]:
    cursor = db.get_cursor()
    cursor.execute(f'SELECT name, monthly_limit '
                   f'FROM categories ')
    rows = cursor.fetchall()
    result = [Category(name=row[0], monthly_limit=row[1]) for row in rows]
    return result
