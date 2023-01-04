import logging
import db

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import Throttled
from aiogram import Bot, Dispatcher, executor, types


API_TOKEN = '5974235292:AAGaFkMwn4j3TuQ8FfJiACRyPsu93WEwJ-E'

logging.basicConfig(level=logging.INFO)

# Storage for throttle control
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Start command handler
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        await dp.throttle('start', rate=2)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 2 секунды перед отправкой следующей')
    else:
        db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        # TODO Add button for the inviter if one does not exist
        # TODO Check for integrity of deep link and inviter
        # TODO Add payment methods choice and integrity checks
        # TODO Increment people invited counter after checking the inviter
        # TODO Add explanations
        # TODO Add info about the inviter
        # TODO Add id checking
        # TODO Add completion message
        # TODO Check if payment information exists if no notify
        # TODO Think up an administration system
        welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'Изменить данные для выплат', 'DEBUG')
        keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
        keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
        await message.answer('Добро пожаловать!', reply_markup=keyboard_markup)

# Help handler
@dp.message_handler(text = "Помощь")
async def send_help(message: types.Message):
    try:
        await dp.throttle('start', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        await message.answer("Текст помощи")

# DEBUG
@dp.message_handler(text = "DEBUG")
async def send_help(message: types.Message):
        db.get_user_data(message.from_user.id)
        await message.answer(message.from_user.id)
# DEBUG

# Payment methods read handler
@dp.message_handler(text = "Просмотреть данные для выплат")
async def echo(message: types.Message):
    try:
        await dp.throttle('Просмотреть данные для выплат', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        await message.answer("Текст просмотра данных для выплат")

# Payment methods change handler
@dp.message_handler(text = "Изменить данные для выплат")
async def echo(message: types.Message):
    try:
        await dp.throttle('Изменить данные для выплат', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        await message.answer("Текст изменения данных для выплат")

# Invite handler
@dp.message_handler(text = "Пригласить нового пользователя")
async def echo(message: types.Message):
    try:
        await dp.throttle('Изменить данные для выплат', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        await message.answer("Текст приглашения")

# Default handler
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("Пожалуйста введите корректную команду или отправьте /start для вызова меню")

# Polling start
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)