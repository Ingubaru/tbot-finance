# import datetime
import logging
# import re
# import pytz
# import exceptions
import db
import config
from utils import get_now_datetime_formatted
from typing import List, NamedTuple, Optional


class Expense(NamedTuple):
    id: Optional[int]
    amount: int
    category: str
    comment: str


def add_expense(expense: Expense) -> int:
    """
    Add expense
    :return: database ID of expense
    """
    expense_dict = {
        'amount': expense.amount,
        'created': get_now_datetime_formatted(config.TIMEZONE),
        'comment': expense.comment,
        'category': expense.category
    }
    inserted_row_id = db.insert("expenses", expense_dict)
    return inserted_row_id


def delete_expense(row_id: int) -> None:
    db.delete('expenses', row_id)


def get_today_statistic() -> List[Expense]:
    """
    Returns today's expense statistics as a string
    :return: statisctic string
    """
    cursor = db.get_cursor()
    cursor.execute(f'SELECT id, amount, category, comment '
                   f'FROM expenses '
                   f'WHERE date(created) >= date("now", "start of day") '
                   f'AND date(created) < date("now", "start of day", "+1 day") ')
    rows = cursor.fetchall()
    result = [Expense(id=row[0], amount=row[1], category=row[2], comment=row[3]) for row in rows]
    return result
