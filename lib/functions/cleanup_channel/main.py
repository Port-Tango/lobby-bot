import os
import yaml
import functions_framework
from database import get_lobby
from messages import get_messages, delete_message, bulk_delete_messages
from utils import calc_age_seconds

ENV = os.getenv('ENV')

with open('channels.yaml', 'r', encoding='utf-8') as file:
  channels_config = yaml.safe_load(file)

LOBBY_CHANNELS = channels_config[ENV]['lobby_channels']

@functions_framework.http
def handler(request):
  # pylint: disable=unused-argument
  for channel in LOBBY_CHANNELS:
    messages_to_delete = []
    messages = get_messages(channel_id=channel)
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
          try:
            lobby = get_lobby(message_id)
            lobby.close()
          except:
            print(f"Failed to close lobby {message_id}")
          messages_to_delete.append(message_id)

    if len(messages_to_delete) == 1:
      delete_message(channel_id=channel, message_id=messages_to_delete[0])

    if len(messages_to_delete) > 1:
      bulk_delete_messages(channel_id=channel, messages=messages_to_delete)

  return "OK", 200
