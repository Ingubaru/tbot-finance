import logging
import config
import exceptions
import db
import os
import expenses
from expenses import Expense
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from middlewares import AccessMiddleware
from utils import parse_expence_message


# TODO: Remove
# import plotly.graph_objects as go


TELEGRAM_API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")
ACCESS_ID = int(os.getenv("TELEGRAM_ACCESS_ID"))


logging.basicConfig(level=logging.INFO)


bot = Bot(token=TELEGRAM_API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(AccessMiddleware(ACCESS_ID))


# TODO: Remove
# sns_labels = groups
# sns_values = [100, 5000, 0, 245, 432, 1231, 10434, 345, 5000]
# fig = go.Figure(data=[go.Pie(values=sns_values,
#                              labels=sns_labels,
#                              textinfo='label+value',
#                              hole=.3)])
# fig.write_image('./static/today.png', width=768, height=768)


class ExpenceState(StatesGroup):
    amount = State()
    category = State()


async def setup_bot_commands(dispatcher):
    bot_commands = [
        types.BotCommand(command="/today", description="Статистика за сегодня"),
        # types.BotCommand(command="/month", description="Статистика за месяц"),
        # types.BotCommand(command="/prev_month", description="Статистика за предыдущий месяц"),
        # types.BotCommand(command="/year", description="Статистика за год"),
        types.BotCommand(command="/help", description="Справка")
    ]
    await dispatcher.bot.set_my_commands(bot_commands)


@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Отправляет приветственное сообщение и помощь по боту"""
    await message.reply(f'Удалить трату: /del <code>ID</code>\n'
                        f'Справка: /help', parse_mode='HTML')


@dp.message_handler(commands=['today'])
async def send_today_expenses(message: types.Message):
    """Отправляет траты за сегодняшний день"""
    today_expenses = expenses.get_today_statistic()

    # Checking for expenses today
    if not today_expenses:
        await message.answer('Сегодня еще нет расходов')
        return

    sum_today_expenses = 0
    today_expenses_str = '{:>7.7} {:<16.16} {:>5.5}\n'.format('[ID]', 'КОММЕНТАРИЙ', 'СУММА')
    for expense in today_expenses:
        exp_id, amount, category, comment = expense.id, int(expense.amount), expense.category, expense.comment
        sum_today_expenses += amount
        today_expenses_str += "{:>7.7} {:<16.16} {:>5d}\n".format(
            '[' + str(exp_id) + ']',
            comment if comment != '' else category,
            amount)
    today_expenses_str += "\n{:7.7} {:<15.15} {:>6d}\n".format('', 'ИТОГО', sum_today_expenses)
    today_expenses_str = '<pre>' + today_expenses_str + '</pre>'
    await bot.send_message(message.from_user.id, today_expenses_str, parse_mode='HTML')


@dp.message_handler(commands=['del'])
async def delete_expense(message: types.Message):
    """Удаляет одну запись о расходе по её идентификатору"""
    row_id = int(message.text[5:])
    expenses.delete_expense(row_id)
    answer_message = "Удалил"
    await message.answer(answer_message)


@dp.message_handler()
async def add_expense(message: types.Message, state: FSMContext):
    try:
        expense = parse_expence_message(message.text)
    except exceptions.NotCorrectMessage as e:
        await message.reply(str(e), reply=False)
        return

    await state.update_data(amount=expense['amount'])
    await state.update_data(comment=expense['comment'])

    # Add keyboard
    category_kb = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=3)
    category_kb.add(*config.CATEGORIES)

    category_msg = await message.reply(f'Укажите категорию', reply_markup=category_kb)
    await state.update_data(msg_id=category_msg.message_id)
    await ExpenceState.category.set()


@dp.message_handler(state=ExpenceState.category)
async def select_group(message: types.Message, state: FSMContext):
    # try:
    #     expense = parse_expence_message(message.text)
    # except exceptions.NotCorrectMessage as e:
    #     await message.reply(str(e), reply=False)
    #     return
    #
    # await state.update_data(amount=expense['amount'])
    # await state.update_data(comment=expense['comment'])
    # await state.update_data(msg_id=message.message_id)
    #
    # # Add keyboard
    # kb = types.InlineKeyboardMarkup(row_width=2)
    # for i in range(0, len(groups), 2):
    #     btn_1 = types.InlineKeyboardButton(groups[i+0], callback_data=f'?group:{groups[i+0]}')
    #     if i + 1 == len(groups):
    #         kb.row(btn_1)
    #     else:
    #         btn_2 = types.InlineKeyboardButton(groups[i+1], callback_data=f'?group:{groups[i+1]}')
    #         kb.row(btn_1, btn_2)
    #
    # await message.reply(f'Укажите категорию', reply_markup=kb)
    # await ExpenceState.group.set()
    await state.update_data(category=message.text)
    data = await state.get_data()
    amount = data['amount']
    comment = data['comment']
    category = data['category']
    msg_id = data['msg_id']
    expense = Expense(
        id=None,
        amount=amount,
        comment=comment,
        category=category
    )
    expense_id = expenses.add_expense(expense)
    await bot.send_message(message.from_user.id,
                           f'<pre>ID {expense_id}\nДобавлено в {category}:\n{amount} {comment}</pre>',
                           parse_mode='HTML')
    await bot.delete_message(
        chat_id=message.from_user.id,
        message_id=msg_id
    )
    await bot.delete_message(
        chat_id=message.from_user.id,
        message_id=message.message_id
    )
    await state.finish()
    pass


# @dp.callback_query_handler(lambda message: message.data.startswith('?group'), state=ExpenceState.group)
# async def answer(call: types.CallbackQuery, state: FSMContext):
#     await state.update_data(group=call.data.split(':')[1])
#     data = await state.get_data()
#
#     amount = data['amount']
#     comment = data['comment']
#     group = data['group']
#     msg_id = data['msg_id']
#
#     await bot.delete_message(
#         chat_id=call.from_user.id,
#         message_id=call.message.message_id
#     )
#     await bot.delete_message(
#         chat_id=call.from_user.id,
#         message_id=msg_id
#     )
#     await call.answer()
#
#     if comment != '':
#         answer_text = f'<i>{comment.capitalize()}</i>\n<code>{group}: {amount} руб\n</code>'
#     else:
#         answer_text = f'<code>{group}: {amount} руб\n</code>'
#     await call.message.answer(answer_text, parse_mode='HTML')
#     await state.finish()


if __name__ == '__main__':
    db.check_exists()
    executor.start_polling(dp, on_startup=setup_bot_commands)
