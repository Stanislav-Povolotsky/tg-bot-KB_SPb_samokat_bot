# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
import os
import json
from _common import *
from aiogram import Bot, Dispatcher, executor, types
from bot_admin_filter import *
from bot_users_filter import *
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
import sbcs_api
import frequency_limits
import qr_gen

API_TOKEN = get_configuration("telegram_token")
AVAILABLE_COMMANDS = [
  {'command': "/help",                  'description': "Помощь"}, 
  {'command': "/menu",                  'description': "Меню"},
  {'command': "/user_info",             'description': "Информация о пользователе"},
  {'command': "/get_pass",              'description': "Получить пропуск на грузовой лифт", "allowed_user_only": True},
  {'command': "/set_my_phone",          'description': "Задать свой номер телефона, на который выписывается пропуск", "allowed_user_only": True},
  {'command': "/set_api_token",         'description': "Задать новый токен для sbcs API", "admin_only": True},
  {'command': "/check_api_token",       'description': "Проверить работоспособность текущего токена для sbcs API", "admin_only": True},
  {'command': "/admins",                'description': "Список администраторов", "admin_only": True},
  {'command': "/admin_add",             'description': "Добавить пользователя в группу администраторов", "admin_only": True},
  {'command': "/admin_del",             'description': "Удалить пользователья из администраторов", "admin_only": True},
  {'command': "/allowed_users",         'description': "Список пользователей, которым разрешено пользоваться ботом", "admin_only": True},
  {'command': "/allowed_user_add",      'description': "Добавить пользователя в список разрешённых пользователей", "admin_only": True},
  {'command': "/allowed_user_del",      'description': "Удалить пользователья из списка разрешённых пользователей", "admin_only": True},
]

btn_share_contact = KeyboardButton('Задать свой номер телефона', request_contact=True)
btn_get_pass = KeyboardButton('Получить пропуск')
btn_help = KeyboardButton('Помощь')

# Configure logging
log = get_logger()

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
admin_filter_activate(dp)
allowed_user_filter_activate(dp)

def get_menu_buttons(user):
    menu_buttons = ReplyKeyboardMarkup(resize_keyboard=True)
    is_allowed = is_allowed_user(user)
    if(is_allowed):
      phone_number = get_allowed_user_profile(user, 'phone_number')
      if(phone_number):
        menu_buttons.add(btn_get_pass)
      else:
        menu_buttons.add(btn_share_contact)
    menu_buttons.add(btn_help)
    return menu_buttons

def get_log_ctx_text(message: types.Message):
    return "[user %s msg %s]" % (message.from_user.id, message.message_id)

def log_request(message: types.Message, ex_text = ""):
    info = []
    text = message.text or message.caption
    if(text): 
      if(text[0] == '/'):
        info.append("Command: " + text)
      else:
        info.append("Text: " + text)
    if(ex_text):
      info.append(ex_text)
    info = ("; ".join(info)).replace("\n", ";\\n ")
    log.debug("Req %s: %s" % (get_log_ctx_text(message), info))

def log_response_fatal_error(message: types.Message, exception):
    info = str(exception).replace("\n", ";\\n ")
    log.error("Res %s fatal error: %s" % (get_log_ctx_text(message), info))

def log_response(message: types.Message, response_text):
    info = str(response_text).replace("\n", ";\\n ")
    log.debug("Res %s: %s" % (get_log_ctx_text(message), info))

@dp.message_handler(commands=['start'])
async def on_command_start(message: types.Message):
    """
    This handler will be called when user sends `/start` command
    """
    try:
      log_request(message)
      response_text = ("Привет! Я помогаю выписывать пропуск на грузовой лифт для самоката.\n" + 
        "Порядок действий:\n" +
        "- Таня должна добавить тебя в список пользователей, которым разрешено пользоваться этим ботом (команда /user_info должна показывать наличие роли 'allowed-user')\n" +
        "- Задай свой номер, на который выписывается пропуск (команда /set_my_phone)\n" +
        "- Получай пропуск (команда /get_pass)")
      log_response(message, response_text)
      await message.reply(response_text,
        reply_markup=get_menu_buttons(message.from_user))
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['help'])
async def on_command_help(message: types.Message):
    """
    This handler will be called when user sends `/help` command
    """
    try:
      log_request(message)
      is_admin = is_admin_user(message.from_user)
      is_allowed = is_allowed_user(message.from_user)
      reply_text = "\n".join([f"*{cmd['command']}* - {cmd['description']}" 
        for cmd in AVAILABLE_COMMANDS if ((is_admin or not("admin_only" in cmd) or not(cmd["admin_only"])) and
          (is_allowed or not("allowed_user_only" in cmd) or not(cmd["allowed_user_only"])))])
      reply_text += "\n\nЕсли что-то не работает, пишите в группу поддержки бота: https://t.me/+oBj2Rfqua3AxMWY6"
      log_response(message, reply_text)
      await message.reply(reply_text, parse_mode="Markdown", reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(lambda message: message.text == btn_help.text)
async def on_btn_help(message: types.Message):
    """
    This handler will be called when user click on `Help` button
    """
    return await on_command_help(message)

@dp.message_handler(commands=['get_pass'], global_allowed_user=True)
async def on_command_get_pass(message: types.Message):
    """
    This handler will be called when user sends `/get_pass` command
    """
    try:
      log_request(message)
      try:
        phone_number = get_allowed_user_profile(message.from_user, 'phone_number')
        if not phone_number:
          raise Exception("Не заполнен номер телефона")
        frequency_limits.check_frequency_limit(message.from_user, 'get_pass')
        code1 = await sbcs_api.get_pass(sbcs_api.read_api_token(), phone_number)
        log.info("Got pass for user %s with phone %s: code1 = %s" % (message.from_user.id, phone_number, code1))
        code1_text = f" ({code1})" if code1 else ""
        response_text = f"Запрос на пропуск был успешно отправлен в систему БЦ.\n" + \
          f"Ожидайте *КОД 1*{code1_text} в SMS на телефон {phone_number}, после чего:\n" + \
          f"Шаг 1: этот *КОД 1*{code1_text} из SMS надо продиктовать охраннику, чтобы получить от него *КОД 2*\n" + \
          f"Шаг 2: ввести *КОД 2* на терминале рядом с охранником, терминал распечатает QR-код для грузового лифта." + "\n\n*Экспериментальная функция*: отправьте *КОД 2* этому боту (просто число), и он сформирует QR-код"
      except Exception as e:
        response_text = "Ошибка: %s" % e 
      log_response(message, response_text)
      await message.reply(response_text, parse_mode="Markdown", reply = False, reply_markup=get_menu_buttons(message.from_user))
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(lambda message: (message.text == btn_get_pass.text and is_allowed_user(message.from_user)))
async def on_btn_get_pass(message: types.Message):
    """
    This handler will be called when user click on `Get Pass` button
    """
    return await on_command_get_pass(message)

@dp.message_handler(commands=['menu'])
async def on_command_menu(message: types.Message):
    """
    This handler will be called when user sends `/menu` command
    """
    try:
      log_request(message)
      response_text = "Menu"
      log_response(message, response_text)
      await message.reply(response_text, reply = False, reply_markup=get_menu_buttons(message.from_user))
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['user_info'])
async def on_command_id(message: types.Message):
    """
    This handler will be called when user sends `/admins` command
    """
    try:
      log_request(message)
      user_info = []
      user_info.append("ID: %d" % message.from_user.id)
      user_info.append("Имя: %s" % message.from_user.username)
      phone_number = get_allowed_user_profile(message.from_user, 'phone_number')
      user_info.append("Телефон: %s" % (phone_number if (phone_number is not None) else '<не задан>'))
      roles = []
      if(is_admin_user(message.from_user)):
        roles.append('admin')
      if(is_allowed_user(message.from_user)):
        roles.append('allowed-user')
      user_info.append("Роли: %s" % ", ".join(roles))
      reply_text = "\n".join(user_info)
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

def check_phone_number_valid(phone_number):
  return isinstance(phone_number, str) and re.match('^\+\d{11}$', phone_number)

@dp.message_handler(commands=['set_my_phone'], global_allowed_user=True)
async def on_command_set_my_phone(message: types.Message):
    """
    This handler will be called when user sends `/set_my_phone` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      phone_number = arguments[0].strip() if (len(arguments) >= 1) else ""
      if(not check_phone_number_valid(phone_number)):
        reply_text = "Формат: /set_my_phone <номер-телефон>\n"
        reply_text += "Пример: /set_my_phone +79001234567"
      else:
        if(set_allowed_user_profile_value(message.from_user, 'phone_number', phone_number)):
          reply_text = f"Задан новый номер пользователя: {phone_number}"
        else:
          reply_text = f"Номер телефона не обновлён (остался прежним)"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False, reply_markup=get_menu_buttons(message.from_user))
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(content_types=['contact'])
async def on_btn_share_contact(message: types.Message):
    """
    This handler will be called when user click on `Share contact` button
    """
    try:
      contact = dict(message.contact.__dict__['_values']) if not(message.contact is None) else {}
      #print(contact)
      log_request(message, "Contact: %s" % json.dumps(contact))
      phone_number = contact['phone_number'] if 'phone_number' in contact else ''
      phone_number = re.sub('[^+0-9]', '', phone_number)
      if(phone_number.startswith('8')):
        phone_number = "+7" + phone_number[1:]
      if phone_number and not(phone_number.startswith('+')):
        phone_number = "+" + phone_number
      if(phone_number and check_phone_number_valid(phone_number)):
        contact['phone_number'] = phone_number
      if not check_phone_number_valid(phone_number):
        reply_text = f"Ошибка: номер телефона задан в недопустимом формате: {phone_number}. Ожидается формат +79001234567"
      elif set_allowed_user_profile_values(message.from_user, contact):
        reply_text = f"Задан новый номер пользователя: {phone_number}"
      else:
        reply_text = f"Номер телефона не обновлён (остался прежним)"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False, reply_markup=get_menu_buttons(message.from_user))
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['admins'], global_admin=True)
async def on_command_admins(message: types.Message):
    """
    This handler will be called when user sends `/admins` command
    """
    try:
      log_request(message)
      admins = get_admins_list()
      reply_text = "Администраторы (%u): " % len(admins)
      reply_text += ", ".join(["%s" % get_user_full_display_name(admin) for admin in admins])
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['admin_add'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/admin_add` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      if(len(arguments) < 1):
        reply_text = "Формат: /admin_add <user_id_or_username>"
      else:
        user = normalize_user_id_or_user_name(arguments[0])
        user_str = get_user_full_display_name(user)
        if(add_admin_user(user)):
          reply_text = f"Пользователь {user_str} добавлен в администраторы"
        else:
          reply_text = f"Пользователь {user_str} уже администратор"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['admin_del'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/admin_add` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      if(len(arguments) < 1):
        reply_text = "Формат: /admin_del <user_id_or_username>"
      else:
        user = normalize_user_id_or_user_name(arguments[0])
        user_str = get_user_full_display_name(user)
        if(del_admin_user(user)):
          reply_text = f"Пользователь {user_str} удалён из администраторов"
        else:
          reply_text = f"Пользователь {user_str} не найден в списке администраторов"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['allowed_users'], global_admin=True)
async def on_command_admins(message: types.Message):
    """
    This handler will be called when user sends `/allowed_users` command
    """
    try:
      log_request(message)
      users = get_allowed_users_list()
      reply_text = "Разрешённые пользователи (%u): " % len(users)
      reply_text += ", ".join(["%s" % get_user_full_display_name(user) for user in users])
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['allowed_user_add'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/allowed_user_add` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      if(len(arguments) < 1):
        reply_text = "Формат: /allowed_user_add <user_id_or_username>"
      else:
        user = normalize_user_id_or_user_name(arguments[0])
        user_str = get_user_full_display_name(user)
        if(add_allowed_user(user)):
          reply_text = f"Пользователь {user_str} добавлен в список разрешённых пользователей"
        else:
          reply_text = f"Пользователь {user_str} уже в списке разрешённых пользователей"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['allowed_user_del'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/allowed_user_del` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      if(len(arguments) < 1):
        reply_text = "Формат: /allowed_user_del <user_id_or_username>"
      else:
        user = normalize_user_id_or_user_name(arguments[0])
        user_str = get_user_full_display_name(user)
        if(del_allowed_user(user)):
          reply_text = f"Пользователь {user_str} удалён из списка разрешённых пользователей"
        else:
          reply_text = f"Пользователь {user_str} не находится в списке разрешённых пользователей"
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['set_api_token'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/set_api_token` command
    """
    try:
      log_request(message)
      command, arguments = message.get_full_command()
      arguments = arguments.strip().split()
      token = arguments[0].strip() if len(arguments) >= 1 else ""
      if(token == "Bearer"):
        token = arguments[1].strip() if len(arguments) >= 2 else ""
      if(not token):
        reply_text = "Формат: /set_api_token <API-authorization-token>\n" + \
          "Пример: /set_api_token eyJ0eA.LongLongAPIToken-px6_QQfqwew-Sabcd"
      else:
        try:
          await sbcs_api.check_token(token)
          set_dynamic_cfg_setting("sbcs_api__authorization", token)
          reply_text = "Токен для API успешно сохранён"
        except Exception as e:
          reply_text = "Ошибка проверки токена для API: %s" % e
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(commands=['check_api_token'], global_admin=True)
async def on_command_admin_add(message: types.Message):
    """
    This handler will be called when user sends `/check_api_token` command
    """
    try:
      log_request(message)
      try:
        token = sbcs_api.read_api_token()
        await sbcs_api.check_token(token)
        reply_text = f"Токен проверен. Всё ОК."
      except Exception as e:
        reply_text = f"Ошибка проверки токена для API: %s" % e
      log_response(message, reply_text)
      await message.reply(reply_text, reply = False)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler(regexp='(^[0-9]{5,8}$)')
async def on_text_regex_number(message: types.Message):
    """
    This handler will be called when user sends text with cats request
    """
    try:
      log_request(message, "Generating QR code")
      number = message.text.strip()
      with qr_gen.gen_qr_code_for_text(number) as photo:
        reply_text = 'QR-код для грузового лифта'
        log_response(message, reply_text)
        await message.reply_photo(photo, caption=reply_text)
    except Exception as e:
      log_response_fatal_error(message, e)

@dp.message_handler()
async def on_text_default(message: types.Message):
    try:
      log_request(message)
      answer = "Неподдерживаемый запрос: %s" % message.text
      log_response(message, answer)
      await message.answer(answer)
    except Exception as e:
      log_response_fatal_error(message, e)

if __name__ == '__main__':
    print("Starting bot %s" % get_configuration("telegram_bot_name", "?"))
    log.info("Starting bot %s" % get_configuration("telegram_bot_name", "?"))
    try:
      executor.start_polling(dp, skip_updates=True)
      log.debug("Stopped")
    except Exception as e:
      log.error("Fatal error: %s" % e)