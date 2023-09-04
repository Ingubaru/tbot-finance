import logging
import kaleido
import os

from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from dotenv import load_dotenv

import categories
import config
import db
import exceptions
import expenses
from expenses import Expense
from middlewares import AccessMiddleware

load_dotenv()

TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
ACCESS_ID = [int(user_id) for user_id in os.getenv("TELEGRAM_ACCESS_ID").split(';')]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(AccessMiddleware(ACCESS_ID))


class BotState(StatesGroup):
    get_category = State()


async def setup_bot_commands(dispatcher):
    bot_commands = [
        types.BotCommand(command="/today",  description="Траты за сегодня"),
        types.BotCommand(command="/month",  description="Траты за месяц"),
        types.BotCommand(command="/year",   description="Статистика за год"),
        types.BotCommand(command="/limits", description="Лимиты по категориям"),
        types.BotCommand(command="/help",   description="Справка")
    ]
    await dispatcher.bot.set_my_commands(bot_commands)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и помощь по боту"""
    await message.reply(f'Удалить трату: /del <code>ID</code>\n'
                        f'Справка: /help', parse_mode='HTML')


@dp.message_handler(commands=['del'])
async def delete_expense(message: types.Message):
    """Удаляет одну запись о расходе по её идентификатору"""
    row_id = int(message.text[4:])
    expense = expenses.get_expense_by_id(row_id)
    if not expense:
        await message.answer('Записи с таким ID не существует')
        return
    expenses.delete_expense(row_id)
    answer_message = '<pre>{:<5.5} {:<17.17} {:>5.5}</pre>\nЗапись удалена'.format(
        str(expense.id),
        expense.comment,
        str(expense.amount)
    )
    await message.answer(answer_message, parse_mode='HTML')


@dp.message_handler(commands=['today'])
async def get_today_expenses(message: types.Message):
    today_expenses = expenses.get_expenses('day')
    if not today_expenses:
        await bot.send_message(message.from_user.id, 'Сегодня нет трат')
        return
    await bot.send_message(message.from_user.id, expenses.format_expenses(today_expenses), parse_mode='HTML')


@dp.message_handler(commands=['month'])
async def get_month_expenses(message: types.Message):
    month_expenses = expenses.get_expenses('month')
    if not month_expenses:
        await bot.send_message(message.from_user.id, 'В этом месяце нет трат')
        return
    filename = month_expenses[0].created[5:7] + '.' + month_expenses[0].created[:4]
    graph = open(expenses.to_statistic_graph(month_expenses, filename), 'rb')
    sheet = open(expenses.to_excel(month_expenses, filename), 'rb')
    await bot.send_photo(message.from_user.id, graph)
    await bot.send_document(message.from_user.id, sheet)


@dp.message_handler(commands=['prev_month'])
async def get_prev_month_expenses(message: types.Message):
    prev_month_expenses = expenses.get_expenses_prev('month')
    if not prev_month_expenses:
        await bot.send_message(message.from_user.id, 'В предыдущем месяце нет трат')
        return
    filename = prev_month_expenses[0].created[5:7] + '.' + prev_month_expenses[0].created[:4]
    graph = open(expenses.to_statistic_graph(prev_month_expenses, filename), 'rb')
    sheet = open(expenses.to_excel(prev_month_expenses, filename), 'rb')
    await bot.send_photo(message.from_user.id, graph)
    await bot.send_document(message.from_user.id, sheet)


@dp.message_handler(commands=['year'])
async def get_year_expenses(message: types.Message):
    year_expenses = expenses.get_expenses('year')
    if not year_expenses:
        await bot.send_message(message.from_user.id, 'В этом году нет трат')
        return
    filename = year_expenses[0].created[:4]
    graph = open(expenses.to_statistic_graph(year_expenses, filename), 'rb')
    sheet = open(expenses.to_excel(year_expenses, filename), 'rb')
    await bot.send_photo(message.from_user.id, graph)
    await bot.send_document(message.from_user.id, sheet)


@dp.message_handler(commands=['limits'])
async def get_category_limits(message: types.Message):
    categories_limits = categories.get_categories()
    limits_str = '{:<10.10} {:>6.6}\n'.format('КАТЕГОРИЯ', 'ЛИМИТ')
    for category_limit in categories_limits:
        limits_str += '{:<10.10} {:>6.6}\n'.format(
            category_limit.name,
            str(category_limit.monthly_limit) if category_limit.monthly_limit else '-')
    limits_str = '<pre>' + limits_str + '</pre>'
    await bot.send_message(message.from_user.id, limits_str, parse_mode='HTML')


@dp.message_handler(commands=['set_limit'])
async def set_category_limit(message: types.Message):
    """Добавляет лимит для категории"""
    message_text = message.text[10:]
    name = message_text.split()[0]
    limit = int(message_text.split()[1])
    category = categories.get_category(name)
    if not category:
        await message.answer('Категории с таким именем не существует')
        return
    categories.set_category_limit(name, limit)
    category_limit = categories.get_category(name)
    answer_message = '<pre>ЛИМИТ ДОБАВЛЕН:\n{} {}\n</pre>'.format(
        category_limit.name,
        str(category_limit.monthly_limit)
    )
    await message.answer(answer_message, parse_mode='HTML')


@dp.message_handler()
async def add_expense(message: types.Message, state: FSMContext):
    try:
        expense = expenses.parse_expence_message(message.text)
    except exceptions.NotCorrectMessage as e:
        await message.reply(str(e), reply=False)
        return

    await state.update_data(amount=expense['amount'])
    await state.update_data(comment=expense['comment'])
    await state.update_data(from_user=message.from_user.full_name)

    # Add keyboard
    category_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    category_kb.add(*config.CATEGORIES)

    category_msg = await message.reply(f'Укажите категорию', reply_markup=category_kb)
    await state.update_data(msg_id_for_remove=category_msg.message_id)
    await BotState.get_category.set()


@dp.message_handler(state=BotState.get_category)
async def select_group(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    data = await state.get_data()
    amount = data['amount']
    comment = data['comment']
    category = data['category']
    from_user = data['from_user']
    msg_id_for_remove = data['msg_id_for_remove']
    expense = Expense(
        id=None,
        amount=amount,
        comment=comment,
        category=category,
        from_user=from_user,
        created=''
    )
    expense_id = expenses.add_expense(expense)
    await bot.send_message(
        message.from_user.id,
        f'<pre>ID {expense_id}\n'
        f'Добавлено в {category}:'
        f'\n{amount} {comment}</pre>',
        parse_mode='HTML'
    )
    await bot.delete_message(
        chat_id=message.from_user.id,
        message_id=msg_id_for_remove
    )
    await bot.delete_message(
        chat_id=message.from_user.id,
        message_id=message.message_id
    )
    await state.finish()
    pass


if __name__ == '__main__':
    db.check_exists()
    executor.start_polling(dp, on_startup=setup_bot_commands)
