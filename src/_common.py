# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
import sys
import os
import re
import json
import logging
import logging.handlers

# Common functions:
# - use get_logger() to get common logger
# - use get_data_folder() to get data folder

# Static configurartion: permanent configuration
# - use get_configuration() to get all configuration parameters
# - use get_configuration("telegram_token") to get one configuration parameter

# Dynamic configuration: can be changed at runtime
# - use get_dynamic_cfg() to get dynamic configuration parameters
# - use get_dynamic_cfg("setting_name", "default_value") to get one dynamic configuration parameter
# - use set_dynamic_cfg_setting("setting_name", "new-value") to set dynamic configuration parameter

def get_current_script_folder():
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

def get_data_folder():
    return os.path.join(get_current_script_folder(), "data")

def get_var_folder():
    return os.path.join(get_current_script_folder(), "var")

def get_var_data_folder():
    return os.path.join(get_var_folder(), "data")

def get_logs_folder():
    return os.path.join(get_var_folder(), "logs")

def setup_logger(logs_folder, app_name, level = logging.DEBUG, log_to_stdout = False, log_to_file = True, log_to_stdout_if_no_file = True, log_rotate = True, log_rotate_backups = 5, log_rotate_size = 1024 * 1024 * 100, modules_to_include = [], init_default_logger = False):
  global log
  if logs_folder and (not os.path.exists(logs_folder)):
    os.makedirs(logs_folder)
  #set_logs_folder(logs_folder)
  #set_logs_app_name(app_name)
  all_loggers = []

  if(init_default_logger):
    all_loggers.append(None)
  cur_log = 'current-app' if (app_name is None) else app_name
  all_loggers.append(cur_log)
  all_loggers.extend(modules_to_include)

  #logger.setLevel(logging.INFO)
  #logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter('%(asctime)s | %(levelname)-5s | %(message)s', 
                              '%m-%d-%Y %H:%M:%S')

  stdout_handler = logging.StreamHandler(sys.stdout)
  stdout_handler.setLevel(logging.DEBUG)
  stdout_handler.setFormatter(formatter)

  an = '' if (app_name is None) else '-%s' % app_name
  log_fpath = os.path.join(logs_folder, "log%s.log" % an) if logs_folder else None

  if(log_to_file and log_fpath):
    if(log_rotate):
      file_handler = logging.handlers.RotatingFileHandler(
        log_fpath, maxBytes=log_rotate_size, backupCount=log_rotate_backups)
    else:
      file_handler = logging.FileHandler(log_fpath, 'a', 'utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
  else:
    file_handler = None

  for cur_log in all_loggers:
    logger = logging.getLogger(cur_log)
    logger.setLevel(level)
  
    if(file_handler):
      logger.addHandler(file_handler)
    if log_to_stdout or (log_to_stdout_if_no_file and not(file_handler)):
      logger.addHandler(stdout_handler)
  return logger

g_logger = None
def get_logger():
  global g_logger
  if(g_logger is None):
    init_default_logger = False
    #init_default_logger = True
    g_logger = setup_logger(get_logs_folder(), get_configuration("app_name"), init_default_logger = init_default_logger)
  return g_logger

def read_configuration():
    try:
      cfg_file = os.path.join(get_data_folder(), "settings.json")
      with open(cfg_file, "rt", encoding="utf8") as f:
        data = json.load(f)
      #print("Configuration from file %s: %s" % (cfg_file, data))
      return data
    except Exception as e:
      raise Exception("Unable to read settings file. " + str(e))

g_cfg = None
def get_configuration(setting_name = None, setting_default_value = None):
    global g_cfg
    if(g_cfg is None):
        g_cfg = read_configuration()
        if(g_cfg is None): 
          g_cfg = {}
    cfg = g_cfg
    if not(setting_name is None):
      return cfg[setting_name] if(setting_name in cfg) else setting_default_value
    return cfg

def get_dynamic_configuration_file_name():
  return os.path.join(get_var_data_folder(), "dynamic-settings.json")

def read_dynamic_configuration():
    try:
      cfg_file = get_dynamic_configuration_file_name()
      if(os.path.exists(cfg_file)):
        with open(cfg_file, "rt", encoding="utf8") as f:
          data = json.load(f)
          if(data is None) or (not isinstance(data, dict)): 
            data = {}
      else:
        data = {}
    except Exception as e:
      get_logger().error("Error loading dynamic configuration file: %s" % str(e))
      data = {}
    return data

g_dyn_cfg = None
def get_dynamic_cfg(setting_name = None, setting_default_value = None, force_read = False):
    global g_dyn_cfg
    if(g_dyn_cfg is None) or force_read:
      g_dyn_cfg = read_dynamic_configuration()
    cfg = g_dyn_cfg
    if not(setting_name is None):
      return cfg[setting_name] if(setting_name in cfg) else setting_default_value
    return cfg

def set_dynamic_cfg_setting(setting_name, setting_value):
    global g_dyn_cfg
    g_dyn_cfg = read_dynamic_configuration()
    g_dyn_cfg[setting_name] = setting_value
    cfg = g_dyn_cfg
    try:
      cfg_file = get_dynamic_configuration_file_name()
      with open(cfg_file, "wt", encoding="utf8") as f:
        data = json.dumps(cfg, indent=4, sort_keys=True)
        print(data, file=f, end="")
    except Exception as e:
      get_logger().error("Error saving dynamic configuration file: %s" % str(e))
