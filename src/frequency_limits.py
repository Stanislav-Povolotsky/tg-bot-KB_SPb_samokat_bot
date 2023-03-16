# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
import time
from _common import *

g_last_user_actions_time = {}
def check_frequency_limit(user, action, update_last_used = True, exception_on_violation = True):
  global g_last_user_actions_time
  limits = get_configuration("frequency_limits", {})
  limit = limits[action] if (action in limits) else 0
  if(limit <= 0): return True
  if not(action in g_last_user_actions_time):
    g_last_user_actions_time[action] = {}
  last_user_action_time = g_last_user_actions_time[action]
  user_id = user.id
  last_time = last_user_action_time[user_id] if (user_id in last_user_action_time) else 0
  t = time.time()
  allowed = (not last_time) or (t - last_time) >= limit
  if(allowed and update_last_used):
    last_user_action_time[user_id] = t
  elif(not allowed) and exception_on_violation:
    raise Exception("Too many requests. Please, wait some time before the new attempt (limit: %u seconds)" % limit)
  return allowed


def selftest_main():
   user = lambda: None
   user.id = 222
   check_frequency_limit(user, 'get_pass')
   checked = False
   try:
     check_frequency_limit(user, 'get_pass')
   except Exception as e:
     checked = 'Too many' in str(e)
   assert(checked)
   print("Selftest OK")

if __name__ == '__main__':
   #loop = asyncio.get_event_loop()
   #loop.run_until_complete(self_main())
   selftest_main()
