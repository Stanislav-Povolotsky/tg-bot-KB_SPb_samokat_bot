# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
from _common import *
from typing import List, Union
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import BoundFilter
from bot_admin_filter import *

def get_allowed_users_list():
  res = get_dynamic_cfg('bot_allowed_users', {})
  return res

def get_user_full_display_name(id_or_username):
  allowed_users = get_dynamic_cfg('bot_allowed_users', {})
  id_or_username = uf_normalize_user_id_or_user_name(id_or_username)
  info = allowed_users[id_or_username] if (id_or_username in allowed_users) else {}
  res = normalize_user_id_or_user_name_display(id_or_username)
  if info:
    ex_info = []
    username = ""
    if('user_id' in info) and (str(info['user_id']) != id_or_username):
      ex_info.append("ID: %s" % info['user_id'])
    if('username' in info) and (str(info['username']) != id_or_username):
      username = info['username']
      ex_info.append("Ник: @%s" % username)
    first_last = []
    if('first_name' in info) and info['first_name']:
      first_last.append(info['first_name'])
    if('last_name' in info) and info['last_name']:
      first_last.append(info['last_name'])
    if first_last:
      ex_info.append("Имя: %s" % " ".join(first_last))
    if(ex_info):
      res += " (%s)" % "; ".join(ex_info)
  return res


def uf_normalize_user_id_or_user_name(id_or_username):
  return str(normalize_user_id_or_user_name(id_or_username))

def add_allowed_user(id_or_username):
  users_dyn = get_dynamic_cfg('bot_allowed_users', {}, force_read = True)
  id_or_username = uf_normalize_user_id_or_user_name(id_or_username)
  if not(id_or_username in users_dyn):
    users_dyn[id_or_username] = {}
    set_dynamic_cfg_setting('bot_allowed_users', users_dyn)
    return True
  else:
    return False

def del_allowed_user(id_or_username):
  users_dyn = get_dynamic_cfg('bot_allowed_users', {}, force_read = True)
  id_or_username = uf_normalize_user_id_or_user_name(id_or_username)
  if (id_or_username in users_dyn):
    del users_dyn[id_or_username]
    set_dynamic_cfg_setting('bot_allowed_users', users_dyn)
    return True
  else:
    return False

def is_allowed_user(user):
  allowed_users = get_allowed_users_list()
  return (str(user.id) in allowed_users) or (user.username in allowed_users) or is_admin_user(user)

def get_allowed_user_profile(user, profile_setting = None, profile_setting_defalt_value = None):
  allowed_users = get_allowed_users_list()
  info = allowed_users[str(user.id)] if (str(user.id) in allowed_users) else allowed_users[user.username] if (user.username and (user.username in allowed_users)) else {}
  if not(profile_setting is None):
    info = info[profile_setting] if (profile_setting in info) else profile_setting_defalt_value
  return info

def set_allowed_user_profile_values(user, values_dict):
  if(is_allowed_user(user)):
    users_dyn = get_dynamic_cfg('bot_allowed_users', {}, force_read = True)
    key = str(user.id) if (str(user.id) in users_dyn) else user.username if not(user.username is None) else str(user.id)
    if not(key in users_dyn):
      users_dyn[key] = {}
    values_dict = dict(values_dict)
    values_dict['user_id'] = user.id
    if(user.username):
      values_dict['username'] = user.username
    same_values = True
    for k,v in values_dict.items():
      if not(k in users_dyn[key]) or (users_dyn[key][k] != v):
        same_values = False
    if(same_values):
      return False
    else:
      for k,v in values_dict.items():
        users_dyn[key][k] = v
      set_dynamic_cfg_setting('bot_allowed_users', users_dyn)
    return True
  return False

def set_allowed_user_profile_value(user, profile_setting, profile_setting_value):
  return set_allowed_user_profile_values(user, {profile_setting: profile_setting_value})

def get_user_phone(user):
  get_allowed_users_list()

class GlobalAllowedUsersFilter(BoundFilter):
    """
    Check if the user is a bot admin
    """
    key = "global_allowed_user"

    def __init__(self, global_allowed_user: bool):
        self.global_allowed_user = global_allowed_user

    async def check(self, obj: Union[types.Message, types.CallbackQuery]):
        user = obj.from_user
        if is_allowed_user(user):
            return self.global_allowed_user is True
        return self.global_allowed_user is False

def allowed_user_filter_activate(dispatcher):
  #  Binding filters
  dispatcher.filters_factory.bind(
      GlobalAllowedUsersFilter,
      exclude_event_handlers=[dispatcher.channel_post_handlers, dispatcher.edited_channel_post_handlers],
  )
