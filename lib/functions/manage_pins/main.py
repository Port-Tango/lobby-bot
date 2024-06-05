import os
import yaml
import functions_framework
from messages import get_messages, update_message, create_pinned_message

ENV = os.getenv('ENV')

with open('channels.yaml', 'r', encoding='utf-8') as file:
  channels_config = yaml.safe_load(file)

LOBBY_CHANNELS = channels_config[ENV]['lobby_channels']

PINNED_MESSAGE = '''
How to **create** a new lobby:
1. set your in-game username using `/lobby set username` **you only need to do this once**
2. set you your `island_id` using `/lobby set island` **you only need to do this once**
  - To find your `island_id`, from Nifty's website navigate `my profile` >> `islands` >> `more details` and get it from the url
3. start typing `/lobby create` and you will be prompted with different commands for the different game types
'''

@functions_framework.http
def handler(request):
  # pylint: disable=unused-argument
  for channel in LOBBY_CHANNELS:
    pinned_message_id = None
    messages = get_messages(channel_id=channel)
    for message in messages:
      message_id = message.get('id')
      is_bot = message['author'].get('bot', False)
      is_pinned = message.get('pinned', False)
      if is_pinned and is_bot:
        pinned_message_id = message_id

    if pinned_message_id:
      update_message(channel_id=channel, message_id=pinned_message_id, content=PINNED_MESSAGE)

    else:
      create_pinned_message(channel_id=channel, content=PINNED_MESSAGE)

  return "OK", 200
