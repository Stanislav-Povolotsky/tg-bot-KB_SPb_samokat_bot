# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
from _common import *
from typing import List, Union
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter

def get_admins_list():
  admins_perm = get_configuration('bot_admins', [])
  admins_dyn = get_dynamic_cfg('bot_admins', [])
  admins = admins_perm + admins_dyn
  return admins

def normalize_user_id_or_user_name(id_or_username):
  if(str(id_or_username).startswith('@')):
    id_or_username = id_or_username[1:]
  try:
    user_id = int(id_or_username)
    id_or_username = user_id
  except:
    pass
  return id_or_username

def normalize_user_id_or_user_name_display(id_or_username):
  id_or_username = normalize_user_id_or_user_name(id_or_username)
  if(isinstance(id_or_username, str)):
    id_or_username = '@' + id_or_username
  elif(isinstance(id_or_username, int)):
    id_or_username = str(id_or_username)
  return id_or_username

def add_admin_user(id_or_username):
  admins_dyn = get_dynamic_cfg('bot_admins', [], force_read = True)
  id_or_username = normalize_user_id_or_user_name(id_or_username)
  if not(id_or_username in admins_dyn):
    admins_dyn.append(id_or_username)
    set_dynamic_cfg_setting('bot_admins', admins_dyn)
    return True
  else:
    return False

def del_admin_user(id_or_username):
  admins_dyn = get_dynamic_cfg('bot_admins', [], force_read = True)
  id_or_username = normalize_user_id_or_user_name(id_or_username)
  if (id_or_username in admins_dyn):
    admins_dyn.remove(id_or_username)
    set_dynamic_cfg_setting('bot_admins', admins_dyn)
    return True
  else:
    return False

def is_admin_user(user):
  admins = get_admins_list()
  return (user.id in admins) or (user.username in admins)

class GlobalAdminFilter(BoundFilter):
    """
    Check if the user is a bot admin
    """
    key = "global_admin"

    def __init__(self, global_admin: bool):
        self.global_admin = global_admin

    async def check(self, obj: Union[types.Message, types.CallbackQuery]):
        user = obj.from_user
        if is_admin_user(user):
            return self.global_admin is True
        return self.global_admin is False

def admin_filter_activate(dispatcher):
  #  Binding filters
  dispatcher.filters_factory.bind(
      GlobalAdminFilter,
      exclude_event_handlers=[dispatcher.channel_post_handlers, dispatcher.edited_channel_post_handlers],
  )
