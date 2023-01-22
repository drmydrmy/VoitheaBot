import logging
import db
import re

from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils.exceptions import Throttled
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram import Bot, Dispatcher, executor, types
from aiogram.utils.deep_linking import get_start_link
from aiogram.utils.callback_data import CallbackData
from aiogram.types import InputFile



API_TOKEN = '5825286084:AAFFqKujAgFN9MuwdWGjmmYFji8XRbtysTQ'
ADMINS_LIMIT = 6
ORDERS_LIMIT = 4

logging.basicConfig(level=logging.INFO)

def create_main_keyboard(user_data):
    welcome_btns_text = ('📝Посмотреть прайс-услуг.', '☎️Контакты для оформления заказа.', '📩Получить ссылку.',  '✨Сделать свою ссылку уникальной.')
    if user_data['payment_method'] == '' and user_data['payment_data'] == '':
        welcome_btns_text = welcome_btns_text + ('💸Добавить реквизиты.',)
    else:
        welcome_btns_text = welcome_btns_text + ('💸Изменить реквизиты.',)
    welcome_btns_text = welcome_btns_text + ('❓Помощь',)
    if db.check_user_is_admin(user_data['user_id']):
        welcome_btns_text = welcome_btns_text + ('Панель администрирования',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    return keyboard_markup

def create_admin_keyboard(user_data):
    welcome_btns_text = ('Добавить заказ', 'Просмотреть или удалить заказы')
    if db.get_super_admin_value(user_data['user_id']) == 1:
        welcome_btns_text = welcome_btns_text + ('Добавить сотрудника', 'Удалить сотрудника', 'Просмотреть или изменить информацию о сотрудниках')
    welcome_btns_text = welcome_btns_text + ('Главное меню',)
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(*(types.KeyboardButton(text) for text in welcome_btns_text))
    return keyboard_markup

def divide_money(sum, system_percent):
    system_sum = sum * (system_percent / 100)
    sum_for_boss_and_first = system_sum * (18.75 / 100)
    inviter_sum = system_sum * (6.25 / 100)
    others_sum = system_sum * (75 / 100)
    sum_dict = {
        'sum_for_boss_and_first' : sum_for_boss_and_first,
        'inviter_sum' : inviter_sum,
        'others_sum' : others_sum
    }
    return(sum_dict)

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

class add_inviter(StatesGroup):
    inviter = State()

class add_order(StatesGroup):
    name = State()
    executor = State()
    client = State()
    handler = State()
    system_percent = State()
    executor_cost = State()

class add_worker(StatesGroup):
    username = State()
    user_data = State()
    is_superadmin = State()

class change_info(StatesGroup):
    username = State()
    info = State()

class delete_user(StatesGroup):
    username = State()
    confirmation = State()

class view_order(StatesGroup):
    view = State()

class delete_order(StatesGroup):
    order_id = State()
    confirmation = State()

class change_link(StatesGroup):
    link = State()

change_page_callback = CallbackData("text", "action", "offset")
view_price_callback = CallbackData("text", "action", "item_name")

# Start command handler
@dp.message_handler(text = "Проверить подписку")
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    try:
        await dp.throttle('start', rate=2)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 2 секунды перед отправкой следующей')
    else:
        db.add_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
        cur_user_data = db.get_user_data(message.from_user.id)
        args = message.get_args()
        if args is None:
            args = ''
        if args != '':
            if (args.isdigit() or db.alias_to_id(args) != -1) and cur_user_data['invited_by'] is None:
                if args.isdigit():
                    if db.check_user_exists(int(args)):
                        if not (db.check_inviter_is_invited(message.from_user.id, int(args))):
                            if not (message.from_user.id == int(args)):
                                db.add_user_invited_by(int(args), message.from_user.id)
                                await message.answer("Пригласитель успешно связан с вашим аккаунтом")
                            else:
                                await message.answer("Вы не можете пригласить себя")
                        else:
                            await message.answer("Пользователь владеющий этой ссылкой был приглашен вами и не может быть вашим пригласителем")
                    else:
                        await message.answer("Неверная ссылка для приглашения или пригласитель не зарегистрирован в боте.")
                else:
                    if not (db.check_inviter_is_invited(message.from_user.id, db.alias_to_id(args))):
                            if not (message.from_user.id == db.alias_to_id(args)):
                                db.add_user_invited_by(db.alias_to_id(args), message.from_user.id)
                                await message.answer("Пригласитель успешно связан с вашим аккаунтом")
                            else:
                                await message.answer("Вы не можете пригласить себя")
                    else:
                            await message.answer("Пользователь владеющий этой ссылкой был приглашен вами и не может быть вашим пригласителем")
            elif not (cur_user_data['invited_by'] is None):
                await message.answer("У вас уже есть код пригласителя. В случае ошибки обратитесь к поддержке")
            elif not args.isdigit() and args != '':
                await message.answer("Неверная ссылка для приглашения.")
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_main_keyboard(cur_user_data)
        join_status = await bot.get_chat_member(-1001880681466, message.from_user.id)
        if join_status['status'] == "member" or join_status['status'] == "administrator" or join_status['status'] == "creator":
            await message.answer('Добро пожаловать!', reply_markup=keyboard_markup)
            await message.answer('Вы можете приглашать новых пользователей используя вашу ссылку. Это позволит вам получить процент с первых трех заказов каждого приглашенного пользователя')
        else:
            decline_keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
            decline_keyboard_markup.add(types.KeyboardButton("Проверить подписку"))
            await message.answer('Мы являемся официальным ботом OPOM VOITHEIA.\nДля использования бота подпишитесь на официальный канал:\nhttps://t.me/OPOM_VOITHEA', reply_markup=decline_keyboard_markup)
        # DONE Check for integrity of deep link and inviter
        # DONE Increment people invited counter after checking the inviter
        # DONE Add explanations
        # DONE Add info about the inviter
        # DONE Add id checking
        # DONE Add completion message
        # DONE Check if payment information exists if no notify
        # DONE Think up an administration system
        # DONE Additional checks on adding an order
        # Invited can't have inviter as his own invited
        # Inviter can't have an invited as his own inviter
        

# Help handler
# @dp.message_handler(text = "Помощь")
# async def send_help(message: types.Message):
#     try:
#         await dp.throttle('start', rate=1)
#     except Throttled:
#         await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
#     else:
#         await message.answer("Текст помощи")

@dp.message_handler(text = '☎️Контакты для оформления заказа.')
async def view_contact_data(message: types.Message):
    await message.reply("Для оформления заказов пишите на телеграмм: \n@VOITHEIA_MSK")

# @dp.message_handler(text = "Просмотреть данные о пригласителе")
# async def check_inviter_data(message: types.Message):
    # try:
    #     await dp.throttle('Просмотреть данные о пригласителе', rate=1)
    # except Throttled:
    #     await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    # else:
    #     cur_user_data = db.get_user_data(message.from_user.id)
    #     if cur_user_data['invited_by'] is None:
    #         keyboard_markup = create_main_keyboard(cur_user_data)
    #         await message.reply("Вы еще не указали пригласителя. Воспользуйтесь командой 'Добавить код пригласителя' или перейдите по специальной ссылке", reply_markup=keyboard_markup)
    #         return
    #     else:
    #         inviter_user_data = db.get_user_data(cur_user_data['invited_by'])
    #         answer_text = "Код пригласителя: " + str(inviter_user_data['user_id']) + "\n" + "Ссылка на аккаунт пригласителя: " + "@" + inviter_user_data['username']
    #         await message.answer(answer_text)

@dp.message_handler(text = "Главное меню")
async def show_main_menu(message: types.Message):
    try:
        await dp.throttle('Главное меню', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_main_keyboard(cur_user_data)
        await message.reply("Главное меню", reply_markup=keyboard_markup)

# Cancel handler
@dp.message_handler(state='*', commands='cancel')
@dp.message_handler(text = "Отмена", state='*')
@dp.message_handler(text = 'НЕТ', state='*')
async def cancel(message: types.Message, state: FSMContext):
    cur_user_data = db.get_user_data(message.from_user.id)
    current_state = await state.get_state()
    if current_state is None:
        return
    logging.info('Cancelling state %r', current_state)
    await state.finish()
    keyboard_markup = create_main_keyboard(cur_user_data)
    await message.reply("Отменено", reply_markup=keyboard_markup)

# DEBUG
# @dp.message_handler(text = "DEBUG")
# async def send_debug(message: types.Message):
#         db.get_user_data(message.from_user.id)
#         await message.answer(message.from_user.id)
# DEBUG

# Payment methods read and change handler

@dp.message_handler(text = '❓Помощь')
async def view_help(message: types.Message):
    await message.reply('💸Добавить/изменить реквизиты.\n[На них вам будет приходить оплата за клиентов.]\n(Банк должен быть подключен к СБП.)\n\n📩Получить ссылку.\n[По этой ссылке мы будем отслеживать приведённых вами людей.]\n\n✨Сделать свою ссылку уникальной.\n[Вы можете выбрать текст своей ссылки]')

@dp.message_handler(text = '📝Посмотреть прайс-услуг.')
async def view_prices_handler(message: types.Message):
    db_prices_data = db.fetch_all_prices()
    price_names_list = ()
    for item in db_prices_data:
        price_names_list = price_names_list + (item[0],)
    inline_keyboard_markup = types.InlineKeyboardMarkup(row_width=2 ,resize_keyboard= True)
    inline_buttons = (types.InlineKeyboardButton(name, callback_data=view_price_callback.new(action = 'view_item', item_name = name)) for name in price_names_list)
    inline_keyboard_markup.add(*inline_buttons)
    await message.reply("🛒 Каталог\n[Оформление подписок Netflix/PlayStation+: @NetflixVoitheaBot]", reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(view_price_callback.filter(action = 'view_item'))
async def view_item_callback_handler(query: types.CallbackQuery, callback_data : dict):
    await query.answer()
    photo_path = "photos/" + callback_data['item_name'] + ".jpg"
    photo = InputFile(photo_path)
    inline_keyboard_markup = types.InlineKeyboardMarkup()
    inline_keyboard_markup.add(types.InlineKeyboardButton("Скрыть", callback_data="Скрыть"))
    await bot.send_photo(query.from_user.id, photo, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(text='Скрыть')
async def hide_item_query_handler(query: types.CallbackQuery):
    await query.answer()
    await query.message.delete()


@dp.message_handler(text = '✨Сделать свою ссылку уникальной.')
async def change_link_handler(message: types.Message):
    cur_alias = db.id_to_alias(message.from_user.id)
    inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard = True)
    inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить ссылку', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='change_link')))
    if cur_alias == -1:
        await message.reply("Вы еще не установили уникальную ссылку", reply_markup=inline_keyboard_markup)
    else:
        message_text = "Ваша уникальная ссылка: \n" + await get_start_link(str(cur_alias))
        await message.reply(message_text, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(change_page_callback.filter(action = 'change_link'))
async def change_link_callback_handler(query: types.CallbackQuery, callback_data : dict):
    await query.answer()
    await change_link.link.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, "Введите до 15 латинских букв и цифр. Ваша ссылка будет иметь формат: \nt.me/opom_voitheia_bot?start=ваш_текст", reply_markup=keyboard_markup)

@dp.message_handler(state=change_link.link)
async def method_change_correct(message: types.Message, state: FSMContext):
    cur_user_data = db.get_user_data(message.from_user.id)
    if len(message.text) > 15:
        await message.reply("Строка должна содержать не больше 15 символов. Попробуйте еще раз")
    else:
        if re.fullmatch(r'[A-Za-z0-9]+', message.text) and message.text != '':
            if db.alias_to_id(message.text) == -1:
                db.change_alias(message.from_user.id, message.text)
                await state.finish()
                keyboard_markup = create_main_keyboard(cur_user_data)
                await message.reply("Ссылка успешно изменена", reply_markup=keyboard_markup)
            else:
                await message.reply("Эта уникальная ссылка уже занята. Попробуйте еще раз")
        else:
            await message.reply("Строка должна содержать только латинские буквы и цифры")


@dp.message_handler(text = "💸Изменить реквизиты.")
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
            keyboard_markup = create_main_keyboard(cur_user_data)
            await message.answer(answer_text, reply_markup= keyboard_markup)
            return
        await message.answer(answer_text, reply_markup=inline_keyboard_markup)

# Inline KB callback handler (payment_method)
@dp.callback_query_handler(text='payment_method')
async def inline_change_payment_method_handler(query: types.CallbackQuery):
    await payment_change.method.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, 'Укажите банк (поддерживающий СБП)', reply_markup=keyboard_markup)
    await query.answer()

# Inline KB callback handler (payment_data)
@dp.callback_query_handler(text='payment_data')
async def inline_change_payment_data_handler(query: types.CallbackQuery):
    await payment_change.data.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, 'Введите данные для выплат (номер телефона начинающийся со знака + или номер карты)', reply_markup=keyboard_markup)
    await query.answer()

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
    keyboard_markup = create_main_keyboard(cur_user_data)
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
    keyboard_markup = create_main_keyboard(cur_user_data)
    await message.reply('Данные успешно изменены', reply_markup= keyboard_markup)
    cur_user_data = db.get_user_data(message.from_user.id)
    inline_keyboard_markup = types.InlineKeyboardMarkup(row_width=1)
    inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить банк', callback_data='payment_method'), types.InlineKeyboardButton('Изменить данные', callback_data='payment_data'))
    answer_text = "Банк: " + cur_user_data['payment_method'] + "\n" + "Данные: " + cur_user_data["payment_data"]
    await message.answer(answer_text, reply_markup=inline_keyboard_markup)

# Payment methods add handler
@dp.message_handler(text = "💸Добавить реквизиты.")
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
    keyboard_markup = create_main_keyboard(cur_user_data)
    await message.reply('Данные успешно сохранены', reply_markup=keyboard_markup)

# Invite handler
@dp.message_handler(text = "📩Получить ссылку.")
async def invite(message: types.Message):
    try:
        await dp.throttle('Пригласить нового пользователя', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        cur_user_data = db.get_user_data(message.from_user.id)
        cur_user_alias = db.id_to_alias(cur_user_data['user_id'])
        if cur_user_alias == -1:
            answer_text = "Количество приглашенных пользователей: " + str(cur_user_data['invited_users_amount']) + "\n" + "Код приглашения: " + str(cur_user_data['user_id']) + "\n" + "Ссылка для приглашения: \n" + await get_start_link(str(cur_user_data['user_id']))
        else: 
            answer_text = "Количество приглашенных пользователей: " + str(cur_user_data['invited_users_amount']) + "\n" + "Код приглашения: " + str(cur_user_data['user_id']) + "\n" + "Ссылка для приглашения: \n" + await get_start_link(cur_user_alias)

        await message.reply(answer_text)

# Add inviter handler
@dp.message_handler(text = "Добавить код пригласителя")
async def add_inviter_handler(message: types.Message):
    try:
        await dp.throttle('Добавить код пригласителя', rate=1)
    except Throttled:
        await message.reply('Вы отправляете команды слишком быстро! Подождите 1 секунду перед отправкой следующей')
    else:
        cur_user_data = db.get_user_data(message.from_user.id)
        if not (cur_user_data['invited_by'] is None):
            keyboard_markup = create_main_keyboard(cur_user_data)
            await message.answer("У вас уже есть код пригласителя. В случае ошибки обратитесь к поддержке", reply_markup=keyboard_markup)
            return
        await add_inviter.inviter.set()
        keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
        keyboard_markup.add(types.KeyboardButton('Отмена'))
        await message.reply("Введите код пригласителя, содержащий только цифры. Вы не сможете сменить его без помощи создателя бота", reply_markup=keyboard_markup)

@dp.message_handler(lambda message: not (message.text.isdigit()), state=add_inviter.inviter)
async def add_inviter_incorrect_format(message: types.Message, state: FSMContext):
    await message.reply("Код должен содержать только цифры. Введите корректный код пригласителя")

@dp.message_handler(lambda message: message.text.isdigit(), state=add_inviter.inviter)
async def add_inviter_correct_format(message: types.Message, state: FSMContext):
    if db.check_user_exists(int(message.text)):
        if not (db.check_inviter_is_invited(message.from_user.id, int(message.text))):
            if message.from_user.id == int(message.text):
                await message.reply("Вы не можете пригласить себя. Введите корректный код пригласителя")
            else:
                await state.finish()
                db.add_user_invited_by(int(message.text), message.from_user.id)
                cur_user_data = db.get_user_data(message.from_user.id)
                keyboard_markup = create_main_keyboard(cur_user_data)
                await message.reply("Пригласитель успешно связан с вашим аккаунтом", reply_markup=keyboard_markup)
        else:
            await message.reply("Пользователь владеющий этим кодом был приглашен вами и не может быть вашим пригласителем. Введите корректный код пригласителя")
    else:
        await message.reply("Неверно введен код или пригласитель не зарегестрирован в боте. Введите корректный код пригласителя")

# Administration part ------------------------------------

@dp.message_handler(text = "Панель администрирования")
async def show_admin_panel(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_admin_keyboard(cur_user_data)
        await message.reply("Добро пожаловать в админ. панель", reply_markup=keyboard_markup)
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.message_handler(text = "Добавить заказ")
async def add_order_command_handler(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        await add_order.name.set()
        keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
        keyboard_markup.add(types.KeyboardButton('Отмена'))
        await message.reply("Введите название или краткое описание заказа", reply_markup=keyboard_markup)
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.message_handler(state=add_order.name)
async def add_order_name_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await add_order.next()
    await message.reply("Введите имя пользователя исполнителя заказа в телеграме, в формате @DrmyDrmy")

@dp.message_handler(state=add_order.executor)
async def add_order_executor_handler(message: types.Message, state: FSMContext):
    if message.text[0] == "@": 
        async with state.proxy() as data:
            data['executor'] = message.text
        await add_order.next()
        await message.reply("Введите имя пользователя клиента в телеграме, в формате @DrmyDrmy")
    else:
        await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(state=add_order.client)
async def add_order_client_handler(message: types.Message, state: FSMContext):
    if message.text[0] == "@": 
        async with state.proxy() as data:
            data['client'] = message.text
        await add_order.next()
        await message.reply("Введите свое имя пользователя в телеграме, в формате @DrmyDrmy")
    else: 
        await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(state=add_order.handler)
async def add_order_handler_handler(message: types.Message, state: FSMContext):
    if message.text[0] == "@": 
        async with state.proxy() as data:
            data['handler'] = message.text
        await add_order.next()
        await message.reply("Введите процентную ставку, в формате 12,5, без знака процента")
    else: 
        await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(state=add_order.system_percent)
async def add_order_system_percent_handler(message: types.Message, state: FSMContext):
    if re.fullmatch(r"[0-9]*\.[0-9]+", message.text.replace(',', '.')) or message.text.isdigit():
        async with state.proxy() as data:
            data['system_percent'] = message.text
        await add_order.next()
        await message.reply("Введите оплату исполнителя, только целые числа")
    else:
        await message.reply("Неверный формат. Введите процент в формате 12,5 без знака процента")

@dp.message_handler(state=add_order.executor_cost)
async def add_order_executor_cost_handler(message: types.Message, state: FSMContext):
    if message.text.isdigit():
        async with state.proxy() as data:
            data['executor_cost'] = message.text
            db.add_order(data['name'], data['executor'], data['client'], data['handler'], data['system_percent'], data['executor_cost'])
        await state.finish()
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_admin_keyboard(cur_user_data)
        await message.reply("Заказ сохранен", reply_markup=keyboard_markup)
    else:
        await message.reply("Неверный формат ввода. Введите целое число без разделителей")

@dp.message_handler(text = "Добавить сотрудника")
async def add_worker_handler(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        if db.get_super_admin_value(message.from_user.id) == 1:
            await add_worker.username.set()
            keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
            keyboard_markup.add(types.KeyboardButton('Отмена'))
            await message.reply("Введите имя пользователя сотрудника в телеграме, пример: @DrmyDrmy. ВНИМАНИЕ, пользователь получит доступ к админ-панели!", reply_markup=keyboard_markup)
        else:
            await message.reply("У вас нет доступа к этой команде")
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.message_handler(lambda message: not (message.text[0] == '@'), state=add_worker.username)
async def add_worker_username_incorrect_handler(message: types.Message, state: FSMContext):
    await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(lambda message: message.text[0] == '@', state=add_worker.username)
async def add_worker_username_correct_handler(message: types.Message, state: FSMContext):
    if db.get_user_id_by_username(message.text) != -1:
        async with state.proxy() as data:
            data['user_id'] = db.get_user_id_by_username(message.text)
        await add_worker.next()
        await message.reply("Введите необходимую информацию о сотруднике (Должность, имя, доп. комментарии)")
    else:
        await message.reply(" Неверно введено имя пользователя или сотрудник не зарегистрирован в боте. Он должен нажать кнопку start или ввести команду /start для регистрации. \n Введите корректное имя пользователя")

@dp.message_handler(state=add_worker.user_data)
async def add_worker_user_data_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['user_info'] = message.text
    await add_worker.next()
    await message.reply("Должен ли сотрудник иметь возможность добавлять новых сотрудников и просматривать данные всех сотрудников? Введите 'ДА' или 'НЕТ'")

@dp.message_handler(state=add_worker.is_superadmin)
async def add_worker_username_handler(message: types.Message, state: FSMContext):
    if message.text == "ДА" or message.text == "НЕТ":
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_admin_keyboard(cur_user_data)
        if message.text == "ДА":
            is_superadmin = 1
            async with state.proxy() as data:
                db.add_admin(data['user_id'], is_superadmin, data['user_info'])
            await state.finish()
            await message.reply("Сотрудник успешно добавлен. Если админ-панель не появилась, он должен отправить /start боту", reply_markup=keyboard_markup)
        if message.text == "НЕТ":
            is_superadmin = 0
            async with state.proxy() as data:
                db.add_admin(data['user_id'], is_superadmin, data['user_info'])
            await state.finish()
            await message.reply("Сотрудник успешно добавлен. Если админ-панель не появилась, он должен отправить /start боту", reply_markup=keyboard_markup)
    else:
        await message.reply("Введите 'ДА' или 'НЕТ'")
    
@dp.message_handler(text = 'Просмотреть или изменить информацию о сотрудниках')
async def check_worker_handler(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        if db.get_super_admin_value(message.from_user.id) == 1:
            row_count = db.get_count_all_rows_admins()
            counter = 1
            answer_text = ''
            data = db.get_page_db_admins(ADMINS_LIMIT, 0)
            for user in data:
                list_user_data = db.get_user_data(user[0])
                if user[2] is None:
                    info = "Информация отсутствует"
                else:
                    info = user[2]
                answer_text += '\n' + str(counter) + ". " + "@" + list_user_data['username'] + '\n' + info + '\n'
                counter += 1
            inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
            if row_count <= ADMINS_LIMIT:
                inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
                await message.answer(answer_text, reply_markup=inline_keyboard_markup)
            else:
                inline_keyboard_markup.add(types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='forward')))
                inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
                await message.answer(answer_text, reply_markup=inline_keyboard_markup)
        else:
            await message.reply("У вас нет доступа к этой команде")
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.callback_query_handler(change_page_callback.filter(action = 'forward'))
async def next_page_admins_query_handler(query: types.CallbackQuery, callback_data : dict):
    row_count = db.get_count_all_rows_admins()
    offset = int(callback_data["offset"])
    answer_text = ''
    counter = offset + 1
    data = db.get_page_db_admins(ADMINS_LIMIT, offset)
    for user in data:
        list_user_data = db.get_user_data(user[0])
        if user[2] is None:
            info = "Информация отсутствует"
        else:
            info = user[2]
        answer_text += '\n' + str(counter) + ". " + "@" + list_user_data['username'] + '\n' + info + '\n'
        counter += 1
    inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton('<--', callback_data=change_page_callback.new(offset=offset - ADMINS_LIMIT, action='back'))]
    if row_count - offset > ADMINS_LIMIT:
        buttons.append(types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=offset + ADMINS_LIMIT, action='forward')))
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)
    else:
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(change_page_callback.filter(action = 'back'))
async def prev_page_admins_query_handler(query: types.CallbackQuery, callback_data : dict):
    offset = int(callback_data["offset"])
    answer_text = ''
    counter = offset + 1
    data = db.get_page_db_admins(ADMINS_LIMIT, offset)
    for user in data:
        list_user_data = db.get_user_data(user[0])
        if user[2] is None:
            info = "Информация отсутствует"
        else:
            info = user[2]
        answer_text += '\n' + str(counter) + ". " + "@" + list_user_data['username'] + '\n' + info + '\n'
        counter += 1
    buttons = [
        types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=offset + ADMINS_LIMIT, action='forward')),
    ]
    inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    if offset > 0:
        buttons.insert(0, types.InlineKeyboardButton('<--', callback_data=change_page_callback.new(offset=offset - ADMINS_LIMIT, action='back')))
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)
    else:
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Изменить информацию о сотруднике', callback_data=change_page_callback.new(offset=ADMINS_LIMIT, action='change_info')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(change_page_callback.filter(action = 'change_info'))
async def change_info_admins_query_handler(query: types.CallbackQuery, callback_data : dict):
    await change_info.username.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, "Введите имя пользователя сотрудника, информацию о котором нужно изменить, в формате @DrmyDrmy", reply_markup=keyboard_markup)
    await query.answer()

@dp.message_handler(lambda message: not (message.text[0] == '@'), state=change_info.username)
async def change_info_username_incorrect_handler(message: types.Message, state: FSMContext):
    await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(lambda message: message.text[0] == '@', state=change_info.username)
async def change_info_username_correct_handler(message: types.Message, state: FSMContext):
    if db.get_user_id_by_username(message.text) != -1:
        async with state.proxy() as data:
            data['user_id'] = db.get_user_id_by_username(message.text)
        await change_info.next()
        await message.reply("Введите необходимую информацию о сотруднике (Должность, имя, доп. комментарии)")
    else:
        await message.reply("Неверно введено имя пользователя. Введите корректное имя пользователя")

@dp.message_handler(state=change_info.info)
async def change_info_info_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        db.change_info_admins(data['user_id'], message.text)
    await state.finish()
    cur_user_data = db.get_user_data(message.from_user.id)
    keyboard_markup = create_admin_keyboard(cur_user_data)
    await message.reply("Информация успешно обновлена", reply_markup=keyboard_markup)

@dp.message_handler(text = 'Удалить сотрудника')
async def delete_user_handler(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        if db.get_super_admin_value(message.from_user.id) == 1:
            await delete_user.username.set()
            keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
            keyboard_markup.add(types.KeyboardButton('Отмена'))
            await message.reply('Введите имя пользователя сотрудника, которого нужно удалить, в формате @DrmyDrmy', reply_markup=keyboard_markup)
        else:
            await message.reply("У вас нет доступа к этой команде")
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.message_handler(lambda message: not (message.text[0] == '@'), state=delete_user.username)
async def delete_user_incorrect_handler(message: types.Message, state: FSMContext):
    await message.reply("Имя пользователя должно начинаться с '@'. Введите корректное имя пользователя")

@dp.message_handler(lambda message: message.text[0] == '@', state=delete_user.username)
async def delete_user_correct_handler(message: types.Message, state: FSMContext):
    if db.get_user_id_by_username(message.text) != -1:
        async with state.proxy() as data:
            data['user_id'] = db.get_user_id_by_username(message.text)
        await delete_user.next()
        await message.reply("Подтвердите удаление. Введите 'ДА' для продолжения, или нажмите 'Отмена'")
    else:
        await message.reply("Неверно введено имя пользователя. Введите корректное имя пользователя")

@dp.message_handler(lambda message: message.text == "ДА", state=delete_user.confirmation)
async def delete_user_confirmed_handler(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        db.delete_admin(data['user_id'])
    await state.finish()
    cur_user_data = db.get_user_data(message.from_user.id)
    keyboard_markup = create_admin_keyboard(cur_user_data)
    await message.reply("Сотрудник удален.", reply_markup=keyboard_markup)

@dp.message_handler(text = 'Просмотреть или удалить заказы')
async def check_all_orders_handler(message: types.Message):
    if db.check_user_is_admin(message.from_user.id):
        row_count = db.get_count_all_rows_orders()
        answer_text = ''
        data = db.get_page_db_orders(ORDERS_LIMIT, 0)
        for order in data:
            answer_text += '\n' + 'Номер заказа: ' + str(order[0]) + "\n" + order[1] + '\n' + order[8] + '\n'
        inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
        if row_count == 0:
            await message.reply("Заказов нет")
        else:
            if row_count <= ORDERS_LIMIT:
                inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
                inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
                await message.answer(answer_text, reply_markup=inline_keyboard_markup)
            else:
                inline_keyboard_markup.add(types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='forward_order')))
                inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
                inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
                await message.answer(answer_text, reply_markup=inline_keyboard_markup)
    else:
        await message.reply("У вас нет доступа к этой команде")

@dp.callback_query_handler(change_page_callback.filter(action = 'forward_order'))
async def next_page_orders_query_handler(query: types.CallbackQuery, callback_data : dict):
    row_count = db.get_count_all_rows_orders()
    offset = int(callback_data["offset"])
    answer_text = ''
    data = db.get_page_db_orders(ORDERS_LIMIT, offset)
    for order in data:
        answer_text += '\n' + 'Номер заказа: ' + str(order[0]) + "\n" + order[1] + '\n' + order[8] + '\n'
    inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    buttons = [types.InlineKeyboardButton('<--', callback_data=change_page_callback.new(offset=offset - ORDERS_LIMIT, action='back_order'))]
    if row_count - offset > ORDERS_LIMIT:
        buttons.append(types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=offset + ORDERS_LIMIT, action='forward_order')))
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
        inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)
    else:
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
        inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(change_page_callback.filter(action = 'back_order'))
async def prev_page_orders_query_handler(query: types.CallbackQuery, callback_data : dict):
    offset = int(callback_data["offset"])
    answer_text = ''
    data = db.get_page_db_orders(ORDERS_LIMIT, offset)
    for order in data:
        answer_text += '\n' + 'Номер заказа: ' + str(order[0]) + "\n" + order[1] + '\n' + order[8] + '\n'
    buttons = [
        types.InlineKeyboardButton('-->', callback_data=change_page_callback.new(offset=offset + ORDERS_LIMIT, action='forward_order')),
    ]
    inline_keyboard_markup = types.InlineKeyboardMarkup(resize_keyboard=True)
    if offset > 0:
        buttons.insert(0, types.InlineKeyboardButton('<--', callback_data=change_page_callback.new(offset=offset - ORDERS_LIMIT, action='back_order')))
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
        inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)
    else:
        inline_keyboard_markup.add(*buttons)
        inline_keyboard_markup.add(types.InlineKeyboardButton('Подробнее о заказе', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='view_order')))
        inline_keyboard_markup.add(types.InlineKeyboardButton('Удалить заказ', callback_data=change_page_callback.new(offset=ORDERS_LIMIT, action='delete_order')))
        await query.answer()
        await bot.delete_message(query.message.chat.id, query.message.message_id)
        await bot.send_message(query.from_user.id, answer_text, reply_markup=inline_keyboard_markup)

@dp.callback_query_handler(change_page_callback.filter(action = 'delete_order'))
async def delete_order_query_handler(query: types.CallbackQuery, callback_data : dict):
    await query.answer()
    await delete_order.order_id.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, "Введите номер заказа", reply_markup=keyboard_markup)

@dp.message_handler(lambda message: not (message.text.isdigit()), state=delete_order.order_id)
async def delete_order_incorrect_handler(message: types.Message, state: FSMContext):
    await message.reply("Номер заказа должен быть цифрой. Введите корректный номер заказа")

@dp.message_handler(lambda message: message.text.isdigit(), state=delete_order.order_id)
async def delete_order_correct_handler(message: types.Message, state: FSMContext):
    if db.check_order_exists(int(message.text)):
        async with state.proxy() as data:
            data['order_id'] = int(message.text)
        await delete_order.next()
        await message.reply("Подтвердите удаление. Введите 'ДА' или 'НЕТ'")
    else:
        await message.reply('Заказа с таким номером не существует. Введите корректный номер заказа')

@dp.message_handler(state=delete_order.confirmation)
async def delete_order_confirmation_handler(message: types.Message, state: FSMContext):
    cur_user_data = db.get_user_data(message.from_user.id)
    if message.text == 'ДА':
        async with state.proxy() as data:
            db.delete_order(data['order_id'])
        await state.finish()
        keyboard_markup = create_admin_keyboard(cur_user_data)
        await message.reply("Заказ удален", reply_markup=keyboard_markup)
    else:
        await message.reply("Введите 'ДА' или 'НЕТ'")

@dp.callback_query_handler(change_page_callback.filter(action = 'view_order'))
async def view_orders_query_handler(query: types.CallbackQuery, callback_data : dict):
    await query.answer()
    await view_order.view.set()
    keyboard_markup = types.ReplyKeyboardMarkup(row_width = 1, resize_keyboard=True)
    keyboard_markup.add(types.KeyboardButton('Отмена'))
    await bot.send_message(query.from_user.id, "Введите номер заказа", reply_markup=keyboard_markup)

@dp.message_handler(lambda message: not (message.text.isdigit()), state=view_order.view)
async def view_order_incorrect_handler(message: types.Message, state: FSMContext):
    await message.reply("Номер заказа должен быть цифрой. Введите корректный номер заказа")

@dp.message_handler(lambda message: message.text.isdigit(), state=view_order.view)
async def view_order_correct_handler(message: types.Message, state: FSMContext):
    if db.check_order_exists(int(message.text)):
        cur_user_data = db.get_user_data(message.from_user.id)
        keyboard_markup = create_admin_keyboard(cur_user_data)
        answer_text = ''
        order_data = db.get_order_data(int(message.text))
        order_sum_data = divide_money(order_data[6], order_data[5])
        order_count_by = db.get_count_orders_by(order_data[3])
        if order_data[7] is None:
            inviter = "Пригласитель отсутствует"
        else:
            inviter_data = db.get_user_data(order_data[7])
            inviter = "Пригласитель: " + "@" + inviter_data['username'] + "\n" + "Банк пригласителя: " + inviter_data['payment_method'] + "\n" + "Платежные данные пригласителя: " + inviter_data['payment_data']
        if order_count_by > 3:
            inviter = "Пользователь совершил больше трех заказов. Данные о пригласителе скрыты"
        answer_text += "Номер: " + str(order_data[0]) + "\n"
        answer_text += "Название: " + order_data[1] + "\n"
        answer_text += "Дата: " + order_data[8] + "\n"
        answer_text += "Исполнитель: " + "@" + order_data[2] + "\n"
        answer_text += "Заказчик: " + "@" + order_data[3] + "\n"
        answer_text += "Сотрудник: " + "@" + order_data[4] + "\n"
        answer_text += "Процентная ставка системы: " + str(order_data[5]) + "%" + "\n"
        answer_text += "Оплата заказа: " + str(order_data[6]) + "\n"
        if not(order_data[7] is None) and order_count_by <= 3:
            answer_text += "Сумма для главного и ближайшего порядка: " + str(order_sum_data['sum_for_boss_and_first']) + "\n"
            answer_text += "Сумма для пригласителя: " + str(order_sum_data['inviter_sum']) + "\n"
        else:
            answer_text += "Сумма для главного и ближайшего порядка: " + str(order_sum_data['sum_for_boss_and_first'] + order_sum_data['inviter_sum']) + "\n"
        answer_text += "Сумма для всех остальных сотрудников: " + str(order_sum_data['others_sum']) + '\n'
        answer_text += inviter
        await state.finish()
        await message.reply(answer_text, reply_markup=keyboard_markup)
    else:
        await message.reply("Заказа с таким номером не существует. Введите корректный номер заказа")

# Default handler
@dp.message_handler()
async def echo(message: types.Message):
    await message.answer("Пожалуйста введите корректную команду или отправьте /start для вызова меню")
    

# Polling start
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)