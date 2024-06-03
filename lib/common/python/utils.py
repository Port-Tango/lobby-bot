import pandas as pd

def calc_age_seconds(timestamp):
  timestamp = pd.Timestamp(timestamp)
  now = pd.Timestamp.now(tz='UTC')
  return (now - timestamp).total_seconds()

def now_iso_str():
  now = pd.Timestamp.now(tz='UTC')
  return now.isoformat()

def wrap_error_message(message: str):
  return f'```diff\n- {message}\n```'

def wrap_success_message(message: str):
  return f'```diff\n+ {message}\n```'
