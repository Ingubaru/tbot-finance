import logging
import os
import sqlite3
import config
from typing import Dict, List

db = sqlite3.connect(os.path.join("db", config.DB_NAME))
cursor = db.cursor()


def get_cursor():
    """
    Return DB cursor
    """
    return cursor


def insert(table: str, column_values: Dict) -> int:
    """
    Insert new row to table
    """
    columns_str = ', '.join(column_values.keys())
    values = [str(i) for i in column_values.values()]
    placeholders = ', '.join('?' * len(column_values.keys()))
    cursor.execute(f'INSERT INTO {table}'
                   f'({columns_str})'
                   f'VALUES ({placeholders})', values)
    row_id = cursor.lastrowid
    db.commit()
    return row_id


def fetchall(table: str, columns: List[str]) -> List[Dict]:
    """
    Fetch all values in columns
    """
    columns_joined = ', '.join(columns)
    cursor.execute(f'SELECT {columns_joined} FROM {table}')
    rows = cursor.fetchall()
    result = []
    for row in rows:
        dict_row = {}
        for index, column in enumerate(columns):
            dict_row[column] = row[index]
        result.append(dict_row)
    return result


def delete(table: str, row_id: int) -> None:
    """
    Delete row by ID
    """
    row_id = int(row_id)
    cursor.execute(f"DELETE FROM {table} WHERE ID={row_id}")
    db.commit()


def check_exists():
    """
    Checks if the database is initialized, if not - initializes DB
    """
    cursor.execute('SELECT name FROM sqlite_master '
                   'WHERE type="table" AND name="expenses"')
    expenses_table_exists = cursor.fetchall()
    if not expenses_table_exists:
        _init_db()


def _init_db():
    """
    Initializes DataBase
    """
    # Create a 'categories' table
    cursor.execute('CREATE TABLE categories('
                   'name VARCHAR(255) PRIMARY KEY,'
                   'monthly_limit INTEGER'
                   ');')
    # Create a 'expenses' table
    cursor.execute('CREATE TABLE expenses('
                   'id INTEGER PRIMARY KEY,'
                   'amount INTEGER,'
                   'created datetime,'
                   'category INTEGER,'
                   'comment text,'
                   'FOREIGN KEY(category) REFERENCES categories(name)'
                   ');')
    # Insert in 'categories' table categories from settings
    for category in config.CATEGORIES:
        cursor.execute(f'INSERT INTO categories'
                       f'(name)'
                       f'VALUES (?)', [category])
    db.commit()
