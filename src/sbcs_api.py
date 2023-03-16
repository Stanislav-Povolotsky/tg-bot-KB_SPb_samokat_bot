# -------------------------------------------------------------------------------------------------
# (C) Stanislav Povolotsky, 2023
# https://github.com/Stanislav-Povolotsky/tg-bot-KB_SPb_samokat_bot
# -------------------------------------------------------------------------------------------------
import asyncio
from _common import *
import aiohttp
import asyncio
import re
import json
import os

log = get_logger()

# HTTP request class
class CRequest:
  def __init__(self, req_params, req_id = 0):
    self.req_id = req_id
    self.req_params = req_params
    self.execution_started = False

  async def execute(self, on_completed = None):
    #print("Started req %u" % self.req_id)
    rp = self.req_params
    new_session = (not('session' in rp) or (rp['session'] is None))
    session = rp['session'] if (not new_session) else aiohttp.ClientSession()
    url = rp['url']
    max_retries_default = 2
    retries = rp['retries'] if ('retries' in rp) else max_retries_default
    method = rp['method'] if ('method' in rp) else 'GET'
    response_json = rp['response_json'] if ('response_json' in rp) else False
    headers = rp['headers'] if ('headers' in rp) else None
    cookies = rp['cookies'] if ('cookies' in rp) else None
    post_data = rp['post_data'] if ('post_data' in rp) else None
    post_json = rp['post_json'] if ('post_json' in rp) else None
    res = {'id': self.req_id, 'response': None, 'status': None, 'error': None, 'request': rp}
    try:
      while(True):
        try:
          res['error'] = None
          res['status'] = 0
          async with session.request(method, url, headers = headers, cookies = cookies, data = post_data, json = post_json) as response:
              res['response'] = response
              res['status'] = response.status
              #print("Status:", response.status)
              #print("Content-type:", response.headers['content-type'])
              if(response_json):
                res['json'] = await response.json()
              else:
                res['html'] = await response.text()
              #print("Body:", html[:15], "...")
        except Exception as e:
          res['error'] = e
        # Retry conditions: http status codes
        retry_error_codes = (500, 400,)
        retry_required = (res['status'] in retry_error_codes)
        # Retry conditions: exceptions
        ex = res['error']
        # [WinError 64] The specified network name is no longer available
        if(ex and (ex is aiohttp.client_exceptions.ClientOSError) and (ex.args[0] != 64)): retry_required = True
        if (not retry_required) or (retries <= 0): break 
        retries -= 1
        await asyncio.sleep(0.1)
      #print("Stopped req %u" % self.req_id)
      if(on_completed):
        await on_completed(self, res)
      else:
        return res
    finally:
      if(new_session):
        await session.close()

def int_lookup_api_definition(api_method_name):
  cfg = get_configuration("sbcs_api")
  if(not cfg):
    raise Exception("Invalid API configuration")
  method_info = cfg['methods'][api_method_name] if ('methods' in cfg) and (api_method_name in cfg['methods']) else None
  if(not method_info):
    log.error("Invalid API method '%s': %s" % (api_method_name, 'not found'))
    raise Exception("Invalid API method '%s'" % api_method_name)
  return method_info

def int_prepare_request(token, api_method_name, method_args = None, data = None):
  method_info = int_lookup_api_definition(api_method_name)
  cfg = get_configuration("sbcs_api")
  req_params = {}
  headers = {}

  if('headers' in cfg):
    headers.update(cfg['headers'])
  if('headers' in method_info):
    headers.update(method_info['headers'])

  authorization_required = method_info['authorization'] if ('authorization' in method_info) else True
  if(authorization_required):
    if(not token):
      raise Exception("API token is not filled")
    headers['Authorization'] = f"Bearer {token}"

  try:
    req_params['url'] = cfg['base_url'] + method_info['url']
    req_params['headers'] = headers
    req_params['method'] = method_info["method"] if ("method" in method_info) else "GET"
    req_params['response_json'] = True
    req_params['headers'] = headers
    if not(data is None):
      req_params['post_json'] = data
  except Exception as e:
    log.error("Error filling request parameters for method '%s': %s" % (api_method_name, e))
    raise Exception("Invalid API method '%s' configuration description" % api_method_name)

  req = CRequest(req_params)
  req.api_method_name = api_method_name
  return req

async def int_execute_request(req):
  try:
    res = await req.execute()
  except Exception as e:
    log.error("Error executing request API method '%s': %s" % (req.api_method_name, e))
    raise Exception("Error executing API method '%s': %s" % (req.api_method_name, e))
  if not('json' in res):
    raise Exception("Error executing API method '%s': no response data" % req.api_method_name)
  data = res['json']
  return data

async def check_token(token):
  req = int_prepare_request(token, 'location_activities')
  data = await int_execute_request(req)
  # "id": 61,
  # "name": "Заказать пропуск"
  expected_activity_id = 61
  expected_activity_name = "Заказать пропуск"
  # "id": "3z9y6et",
  # "name": "Пропуск для доставки/выноса ТМЦ курьерами",
  expected_issue_id = "3z9y6et"
  expected_issue_name = "Пропуск для доставки/выноса ТМЦ курьерами"

  expected_issue_attr_count = 7
  expected_issue_attr_ids = ["3pavd71wx3nb", "8vbl70ztlxov", "_pass_allowed_assets"]

  found_activity = None
  found_issue_type = None
  try:
    for item in data:
      a_id = item['id'] if 'id' in item else None
      a_name = item['name'] if 'name' in item else None
      if(a_id == expected_activity_id) and (a_name == expected_activity_name):
        found_activity = item
        break
    if(not found_activity):
      raise Exception("Expected activity was not found")
  
    act_params = found_activity['params'] if 'params' in found_activity else {}
    act_issue_types = act_params["issue_types"] if (act_params and ("issue_types" in act_params)) else []
    for item in act_issue_types:
      a_id = item['id'] if 'id' in item else None
      a_name = item['name'] if 'name' in item else None
      if(a_id == expected_issue_id) and (a_name == expected_issue_name):
        found_issue_type = item
        break

    if(not found_issue_type):
      raise Exception("Expected issue type was not found")

    issue_attrs = found_issue_type["attributes"] if ("attributes" in found_issue_type) else []
    not_found_attrs = set(expected_issue_attr_ids)
    all_attrs = []
    for item in issue_attrs:
      a_id = item['id'] if 'id' in item else None
      a_name = item['name'] if 'name' in item else None
      a_name_int = item["internal_name"] if "internal_name" in item else None
      all_attrs.append("%s (%s)" % (a_id, a_name))
      if(a_id in not_found_attrs):
        not_found_attrs.remove(a_id)
      if(a_name_int in not_found_attrs):
        not_found_attrs.remove(a_name_int)
    if(not_found_attrs):
      raise Exception("Expected issue attributes were not found: %s" % ", ".join(not_found_attrs))
    if(len(issue_attrs) < expected_issue_attr_count):
      log.warning("Expected issue more attributes. Found only %d: %s" % (len(all_attrs), ", ".join(all_attrs)))
    elif(len(issue_attrs) > expected_issue_attr_count):
      log.warning("Expected issue less attributes. Found %d: %s" % (len(all_attrs), ", ".join(all_attrs)))

  except Exception as e:  
   log.error("Error checking API token: unexpected response data format: %s" % e)
   raise Exception("Error checking API token: unexpected response data format")

  return True

async def get_pass(token, phone_number):
  api_method_name = "create_issue_for_samokat"
  method_info = int_lookup_api_definition(api_method_name)
  data = method_info["data-template"].copy()
  data["attributes"]["3pavd71wx3nb"] = phone_number

  req = int_prepare_request(token, api_method_name, data = data)
  data = await int_execute_request(req)
  try:
    log.debug("Response data %s" % json.dumps(data, ensure_ascii=False))
    code1 = data["data"]["display_id"]
  except Exception as e:
    log.error("Unexpected response data format calling %s: %s" % (api_method_name, e))
    raise Exception("Unexpected response data format")

  return code1

def read_api_token():
  return get_dynamic_cfg("sbcs_api__authorization")

async def self_main():
   token = read_api_token()
   print(f"Current token: {token}")
   try:
     print("Checking token... ", end="")
     await check_token(token)
     print("OK")

     if(0):
       print("Getting pass... ", end="")
       code1 = await get_pass(token, sys.argv[1])
       print("Result: %s. " % code1, end="")
       print("OK")
   except Exception as e:
     print("Error %s" % e)

if __name__ == '__main__':
   loop = asyncio.get_event_loop()
   loop.run_until_complete(self_main())
