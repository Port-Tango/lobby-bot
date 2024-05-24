import functions_framework
from database import get_lobby
from messages import get_messages, delete_message, bulk_delete_messages
from utils import calc_age_seconds

@functions_framework.http
def handler(request):
  print(request.get_json())
  messages_to_delete = []
  messages = get_messages()
  for message in messages:
    message_id = message.get('id')
    is_bot = message['author'].get('bot', False)
    is_pinned = message.get('pinned', False)
    content = message.get('content')
    age_seconds = calc_age_seconds(message['timestamp'])

    if not is_pinned:
      ## non-bot messages
      if not is_bot:
        messages_to_delete.append(message_id)
        continue

      ## failed bot commands older than 5 minutes
      if (not content or content == '') and age_seconds > 300:
        messages_to_delete.append(message_id)
        continue

      ## lobby messages older than 1 hour. Should be handled by other logic
      if is_bot and content and content != '' and age_seconds > 3600:
        lobby = get_lobby(message_id)
        lobby.close()
        messages_to_delete.append(message_id)

  if len(messages_to_delete) == 1:
    delete_message(message_id=messages_to_delete[0])

  if len(messages_to_delete) > 1:
    bulk_delete_messages(messages=messages_to_delete)

  return "OK", 200
