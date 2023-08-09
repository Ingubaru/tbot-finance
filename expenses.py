import datetime
import os
import re

import pandas as pd
import openpyxl
import numpy as np
from typing import List, NamedTuple, Optional

import plotly.graph_objects as go
import pytz

import config
import db
import exceptions


class Expense(NamedTuple):
    id: Optional[int]
    amount: int
    category: str
    comment: str
    from_user: str
    created: str


def add_expense(expense: Expense) -> int:
    """
    Add expense
    :return: database ID of expense
    """
    expense_dict = {
        'amount': expense.amount,
        'created': _get_now_datetime_formatted(config.TIMEZONE),
        'comment': expense.comment,
        'category': expense.category,
        'from_user': expense.from_user,
    }
    inserted_row_id = db.insert("expenses", expense_dict)
    return inserted_row_id


def delete_expense(row_id: int) -> None:
    db.delete('expenses', row_id)


def get_expenses(period: str) -> List[Expense]:
    """
    Returns today's expensesg
    :param period: 'day', 'month', 'year'
    :return: list of Expense
    """
    cursor = db.get_cursor()
    cursor.execute(f'SELECT id, amount, category, comment, from_user, created '
                   f'FROM expenses '
                   f'WHERE date(created) >= date("now", "start of {period}") '
                   f'AND date(created) < date("now", "start of {period}", "+1 {period}") ')
    rows = cursor.fetchall()
    result = [Expense(id=row[0], amount=row[1], category=row[2], comment=row[3], from_user=row[4], created=row[5])
              for row in rows]
    return result


def get_expense_by_id(row_id: int) -> Expense | None:
    cursor = db.get_cursor()
    cursor.execute(f'SELECT id, amount, category, comment, from_user, created '
                   f'FROM expenses '
                   f'WHERE ID={row_id} ')
    row = cursor.fetchone()
    if not row:
        return None
    result = Expense(id=row[0], amount=row[1], category=row[2], comment=row[3], from_user=row[4], created=row[5])
    return result


def get_expenses_prev(period: str) -> List[Expense]:
    """
    Returns the previous month's expenses
    :param period: 'day', 'month', 'year'
    :return: list of Expense
    """
    cursor = db.get_cursor()
    cursor.execute(f'SELECT id, amount, category, comment, from_user, created '
                   f'FROM expenses '
                   f'WHERE date(created) >= date("now", "start of {period}", "-1 {period}") '
                   f'AND date(created) < date("now", "start of {period}") ')
    rows = cursor.fetchall()
    result = [Expense(id=row[0], amount=row[1], category=row[2], comment=row[3], from_user=row[4], created=row[5])
              for row in rows]
    return result


def format_expenses(expenses: List[Expense]) -> str:
    sum_expenses = 0
    expenses_str = '{:<5.5} {:<17.17} {:>5.5}\n'.format('ID', 'КОММЕНТАРИЙ', 'СУММА')
    for expense in expenses:
        sum_expenses += expense.amount
        expenses_str += "{:<5.5} {:<17.17} {:>5d}\n".format(
            str(expense.id),
            expense.comment if expense.comment != '' else expense.category,
            expense.amount)
    expenses_str += "\n{:5.5} {:<16.16} {:>6d}\n".format('', 'ИТОГО', sum_expenses)
    expenses_str = '<pre>' + expenses_str + '</pre>'
    return expenses_str


def to_statistic_graph(expenses: List[Expense], filename: str = '') -> str:
    """
    Create PNG file with pie diagram of expenses
    :return: path to static PNG file
    """
    categories = set([expense.category for expense in expenses])
    categories = list(categories)
    values = []
    for c in categories:
        values.append(np.sum([e.amount if e.category == c else 0 for e in expenses]))
    total = np.sum(values)
    graph = go.Figure(data=[go.Pie(
        values=values,
        labels=categories,
        textinfo='label+value',
        hole=.35)]
    )
    graph.add_annotation(dict(
        font=dict(color='black', size=48),
        text=filename,
        showarrow=False,
        x=-0.1,
        y=1.1
    ))
    graph.add_annotation(dict(
        font=dict(color='black', size=36),
        text=str(total),
        showarrow=False,
    ))
    filepath = os.path.join(config.STATIC_PATH, filename + '.png')
    graph.write_image(filepath, width=768, height=768)
    return filepath


def to_excel(expenses: List[Expense], filename: str) -> str:
    """
    Create EXCEL file with expenses
    :return: path to static EXCEL file
    """
    df = pd.DataFrame(expenses)
    filepath = os.path.join(config.STATIC_PATH, filename + '.xlsx')
    df.to_excel(filepath)
    return filepath


def parse_expence_message(message: str) -> {}:
    """
    Parses the incoming message about the new expense
    """
    regexp_result = re.match(r"([\d ]+) ?(.*)", message, re.DOTALL)
    if not regexp_result or not regexp_result.group(0) or not regexp_result.group(1):
        raise exceptions.NotCorrectMessage(
            "Напишите сообщение в формате:\n"
            "Сумма Коментарий(опционально)"
        )
    amount_raw = int(regexp_result.group(1).replace(" ", ""))
    comment_raw = '' if not regexp_result.group(2) else regexp_result.group(2).strip().lower()
    return {'amount': amount_raw, 'comment': comment_raw}


def _get_now_datetime(timezone: str) -> datetime.datetime:
    """
    Returns today's datetime including time zone
    """
    tz = pytz.timezone(timezone)
    now = datetime.datetime.now(tz)
    return now


def _get_now_datetime_formatted(timezone: str) -> str:
    """
    Returns today's datetime formatted string including timezone
    :return datetime: %Y-%m-%d %H:%M:%S
    """
    return _get_now_datetime(timezone).strftime('%Y-%m-%d %H:%M:%S')
