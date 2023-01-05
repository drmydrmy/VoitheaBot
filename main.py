import logging
import db
import re

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import Throttled
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, executor, types



API_TOKEN = '5974235292:AAGaFkMwn4j3TuQ8FfJiACRyPsu93WEwJ-E'

logging.basicConfig(level=logging.INFO)


# Storage for throttle control
storage = MemoryStorage()
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=storage)

# States
class payment(StatesGroup):
    method = State()
    data = State()

class payment_change(StatesGroup):
    data = State()
    method = State()


# Start command handler
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        await dp.throttle('start', rate=2)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 2 секунды перед отправкой следующей')
    else:
        db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        cur_user_data = db.get_user_data(message.from_user.id)
        # TODO Check for integrity of deep link and inviter
        # TODO Increment people invited counter after checking the inviter
        # TODO Add explanations
        # TODO Add info about the inviter
        # TODO Add id checking
        # TODO Add completion message
        # TODO Check if payment information exists if no notify
        # TODO Think up an administration system
        welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
        if cur_user_data['invited_by'] is None:
            welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
        if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
            welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
        else:
            welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
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

# Cancel handler
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(text = "Отмена", state='*')
async def cancel(message: types.Message, state: FSMContext):
    cur_user_data = db.get_user_data(message.from_user.id)
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    await state.finish()
    welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
    if cur_user_data['invited_by'] is None:
        welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
    if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
        welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
    else:
        welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    await message.reply("Отменено", reply_markup=keyboard_markup)

# DEBUG
@dp.message_handler(text = "DEBUG")
async def send_debug(message: types.Message):
        db.get_user_data(message.from_user.id)
        await message.answer(message.from_user.id)
# DEBUG

# Payment methods read and change handler
@dp.message_handler(text = "Просмотреть или изменить данные для выплат")
async def check_change_payment_data(message: types.Message):
    try:
        await dp.throttle('Просмотреть или изменить данные для выплат', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        inline_keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить банк', callback_data='payment_method'), types.InlineKeyboardButton('Изменить данные', callback_data='payment_data'))
        cur_user_data = db.get_user_data(message.from_user.id)
        answer_text = "Банк: " + cur_user_data['payment_method'] + "\n" + "Данные: " + cur_user_data["payment_data"]
        if cur_user_data['payment_data'] == '' and cur_user_data['payment_method'] == '':
            answer_text = 'Вы еще не указали данные. Используйте команду "Добавить данные для выплат" или /start для вызова меню'
        await message.answer(answer_text, reply_markup=inline_keyboard_markup)

# Inline KB callback handler (payment_method)
@dp.callback_query_handler(text='payment_method')
async def inline_change_payment_method_handler(query: types.CallbackQuery):
    await payment_change.method.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, 'Укажите банк (поддерживающий СБП)', reply_markup=keyboard_markup)

# Inline KB callback handler (payment_data)
@dp.callback_query_handler(text='payment_data')
async def inline_change_payment_data_handler(query: types.CallbackQuery):
    await payment_change.data.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, 'Введите данные для выплат (номер телефона начинающийся со знака + или номер карты)', reply_markup=keyboard_markup)

# Payment data change handler (INcorrect number)
@dp.message_handler(lambda message: not ((re.fullmatch(r'([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?', message.text) or message.text.isdigit()) and len(message.text) < 90), state=payment_change.data)
async def data_change_incorrect(message: types.Message, state: FSMContext):
    await message.reply('Данные могут содержать только цифры и знак +. Введите данные для выплат')

# Payment data change handler (correct number)
@dp.message_handler(lambda message: (re.fullmatch(r'([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?', message.text) or message.text.isdigit()) and len(message.text) < 90, state=payment_change.data)
async def data_change_correct(message: types.Message, state: FSMContext):
    await state.finish()
    cur_user_data = db.get_user_data(message.from_user.id)
    db.change_user_payment_data(message.text, message.from_user.id)
    welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
    if cur_user_data['invited_by'] is None:
        welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
    if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
        welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
    else:
        welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    await message.reply('Данные успешно изменены', reply_markup= keyboard_markup)
    cur_user_data = db.get_user_data(message.from_user.id)
    inline_keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить банк', callback_data='payment_method'), types.InlineKeyboardButton('Изменить данные', callback_data='payment_data'))
    answer_text = "Банк: " + cur_user_data['payment_method'] + "\n" + "Данные: " + cur_user_data["payment_data"]
    await message.answer(answer_text, reply_markup=inline_keyboard_markup)

# Payment method change handler (INcorrect length)
@dp.message_handler(lambda message: not len(message.text) < 30, state=payment_change.method)
async def method_change_incorrect(message: types.Message, state: FSMContext):
    await message.reply('Название банка должно содержать меньше 30 символов. Введите название банка')

# Payment method change handler (correct length)
@dp.message_handler(lambda message: len(message.text) < 30, state=payment_change.method)
async def method_change_correct(message: types.Message, state: FSMContext):
    await state.finish()
    cur_user_data = db.get_user_data(message.from_user.id)
    db.change_user_payment_method(message.text, message.from_user.id)
    welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
    if cur_user_data['invited_by'] is None:
        welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
    if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
        welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
    else:
        welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    await message.reply('Данные успешно изменены', reply_markup= keyboard_markup)
    cur_user_data = db.get_user_data(message.from_user.id)
    inline_keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить банк', callback_data='payment_method'), types.InlineKeyboardButton('Изменить данные', callback_data='payment_data'))
    answer_text = "Банк: " + cur_user_data['payment_method'] + "\n" + "Данные: " + cur_user_data["payment_data"]
    await message.answer(answer_text, reply_markup=inline_keyboard_markup)

# Invited can't have inviter as his own invited
# Inviter can't have an invited as his own inviter
# Payment methods add handler
@dp.message_handler(text = "Добавить данные для выплат")
async def add_payment_data(message: types.Message):
    try:
        await dp.throttle('Добавить данные для выплат', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        cur_user_data = db.get_user_data(message.from_user.id)
        if cur_user_data['payment_method'] != '' or cur_user_data['payment_data'] != '':
            await message.answer("Вы уже добавляли данные для выплат. Используйте команду 'Изменить данные для выплат'")
            return
        await payment.method.set()
        keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
        keyboard_markup.add(types.KeyboardButton('Отмена'))
        await message.answer("Укажите банк (поддерживающий СБП)", reply_markup=keyboard_markup)

# Payment method add state handler (INcorrect length)
@dp.message_handler(lambda message: not len(message.text) < 30, state=payment.method)
async def method_add_incorrect(message: types.Message, state: FSMContext):
    await message.reply('Название банка должно содержать меньше 30 символов. Введите название банка')

# Payment method add state handler (correct length)
@dp.message_handler(lambda message: len(message.text) < 30, state=payment.method)
async def method_add_correct(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['payment_method'] = message.text
    await payment.next()
    await message.reply('Введите данные для выплат (номер телефона начинающийся со знака + или номер карты)')

# Payment data add state handler (INcorrect number)
@dp.message_handler(lambda message: not ((re.fullmatch(r'([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?', message.text) or message.text.isdigit()) and len(message.text) < 90), state=payment.data)
async def data_add_incorrect(message: types.Message, state: FSMContext):
    await message.reply('Данные могут содержать только цифры и знак +. Введите данные для выплат')

# Payment data add state handler (correct number)
@dp.message_handler(lambda message: (re.fullmatch(r'([+-]?(?=\.\d|\d)(?:\d+)?(?:\.?\d*))(?:[eE]([+-]?\d+))?', message.text) or message.text.isdigit()) and len(message.text) < 90, state=payment.data)
async def data_add_correct(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['payment_data'] = message.text
        db.add_user_payment(data['payment_method'], data['payment_data'], message.from_user.id)
    await state.finish()
    cur_user_data = db.get_user_data(message.from_user.id)
    welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
    if cur_user_data['invited_by'] is None:
        welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
    if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
        welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
    else:
        welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    await message.reply('Данные успешно сохранены', reply_markup=keyboard_markup)
# Invite handler
@dp.message_handler(text = "Пригласить нового пользователя")
async def invite(message: types.Message):
    try:
        await dp.throttle('Пригласить нового пользователя', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:

        await message.answer("Текст приглашения")

# Add inviter handler
@dp.message_handler(text = "Добавить код пригласителя")
async def add_inviter(message: types.Message):
    try:
        await dp.throttle('Добавить код пригласителя', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        cur_user_data = db.get_user_data(message.from_user.id)
        if not (cur_user_data['invited_by'] is None):
            welcome_btns_text = ('Помощь', 'Пригласить нового пользователя', 'DEBUG')
            if cur_user_data['invited_by'] is None:
                welcome_btns_text = welcome_btns_text + ('Добавить код пригласителя',)
            if cur_user_data['payment_method'] == '' and cur_user_data['payment_data'] == '':
                welcome_btns_text = welcome_btns_text + ('Добавить данные для выплат',)
            else:
                welcome_btns_text = welcome_btns_text + ('Просмотреть или изменить данные для выплат',)
            keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
            keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
            await message.answer("У вас уже есть код пригласителя. В случае ошибки обратитесь к поддержке", reply_markup=keyboard_markup)
            return
        await message.answer("Текст добавления пригласителя")

# Default handler
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("Пожалуйста введите корректную команду или отправьте /start для вызова меню")

# Polling start
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)