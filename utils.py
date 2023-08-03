import datetime
import re
import pytz
import exceptions


def parse_expence_message(message: str) -> {'amount': int, 'comment': str}:
    """
    Parses the incoming message about the new expense
    """
    regexp_result = re.match(r"([\d ]+) ?(.*)", message, re.DOTALL)
    if not regexp_result or not regexp_result.group(0) or not regexp_result.group(1):
        raise exceptions.NotCorrectMessage(
            "Напишите сообщение в формате:\n"
            "Сумма Коментарий(опционально)"
        )
    amount = int(regexp_result.group(1).replace(" ", ""))
    comment = '' if not regexp_result.group(2) else regexp_result.group(2).strip().lower()
    return {'amount': amount, 'comment': comment}


def get_now_datetime(timezone: str) -> datetime.datetime:
    """
    Returns today's datetime including time zone
    """
    tz = pytz.timezone(timezone)
    now = datetime.datetime.now(tz)
    return now


def get_now_datetime_formatted(timezone: str) -> str:
    """
    Returns today's datetime formatted string including timezone
    :return datetime: %Y-%m-%d %H:%M:%S
    """
    return get_now_datetime(timezone).strftime('%Y-%m-%d %H:%M:%S')
