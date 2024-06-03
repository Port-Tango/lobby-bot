import os
from enum import Enum
import requests
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from database import Lobby
from messages import delayed_delete_ephemeral_message
from interactions import Interaction

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PUBLIC_KEY = os.getenv('BOT_PUBLIC_KEY')
BOT_APP_ID = os.getenv('BOT_APP_ID')
PARTY_CHANNEL = os.getenv('PARTY_CHANNEL')
BASE_URL = 'https://discord.com/api/v10'

headers = {
  'Authorization': f'Bot {BOT_TOKEN}',
  'Content-Type': 'application/json'
}

class RequestType(Enum):
  PING = 1
  APPLICATION_COMMAND = 2
  MESSAGE_COMPONENT = 3

class DiscordErrorType(Enum):
  INVALID_SIGNATURE = 'Invalid signature'
  COMMAND_IN_THREAD = 'Command was used in a thread'
  INVALID_CHANNEL = 'Command was not used in the appropriate channel'
  INVALID_COMMAND = 'Invalid command'
  INVALID_SUBCOMMAND_GROUP = 'Invalid subcommand group'
  INVALID_SUBCOMMAND = 'Invalid or umapped subcommand'

def validate_request(request):
  verify_key = VerifyKey(bytes.fromhex(BOT_PUBLIC_KEY))
  signature = request.headers['X-Signature-Ed25519']
  timestamp = request.headers['X-Signature-Timestamp']
  body = request.data.decode('utf-8')

  try:
    verify_key.verify(f"{timestamp}{body}".encode(), bytes.fromhex(signature))
  except BadSignatureError:
    return False
  return True

def bot_followup_response(interaction: Interaction, ephemeral: bool, json: dict):
  url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{interaction.token}'
  if ephemeral:
    json['flags'] = 64
  reply_response = requests.post(url, json=json, headers=headers)
  reply_response.raise_for_status()
  reply_response_json = reply_response.json()
  message_id = reply_response_json['id']
  if ephemeral:
    delayed_delete_ephemeral_message(
      interaction=interaction,
      delay_in_seconds=20,
      message_id=message_id
    )
  return reply_response_json['id']

def bot_lobby_response(interaction: Interaction, lobby: Lobby):
  url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{interaction.token}/messages/@original'
  components = [
    {
      'type': 1,
      'components': [
        {
          'type': 2,
          'label': 'Join Lobby',
          'style': 1,
          'custom_id': 'join_lobby'
        },
        {
          'type': 2,
          'label': 'Leave Lobby',
          'style': 4,
          'custom_id': 'leave_lobby'
        }
      ]
    }
  ]
  content = f'A new **{lobby.game.game_type}** lobby has been created'
  if lobby.island:
    content += f' for **{lobby.island.name}**!'
  content += '\n**Players in lobby:** '
  content += f'({lobby.player_count}/{lobby.game.min_players})'
  content += lobby.get_party_list(numbered=False, include_island=False)
  content += '\n**Lobby status:**\n```diff\n+ OPEN\n```'
  json = {
    'content': content,
    'components': components,
    'flags': 4 # supress embeds
  }
  reply_response = requests.patch(url, json=json)
  reply_response.raise_for_status()

def bot_party_notification(lobby: Lobby):
  url = f'{BASE_URL}/channels/{PARTY_CHANNEL}/messages'
  if lobby.game.game_type == 'Visit Train':
    starting_island = lobby.players[0].island
    button_label = '🏝️ Join Starting Island 🏝️'
    button_url = starting_island.url
  else:
    button_label = f'🏝️ Join {lobby.island.name} 🏝️'
    button_url = lobby.island.url
  components = [
    {
      'type': 1,
      'components': [
        {
          'type': 2,
          'label': button_label,
          'style': 5,
          'url': button_url
        }
      ]
    }
  ]
  content = f'A new **{lobby.game.game_type}** party of {lobby.game.min_players}'
  content += ' players has been matched!'
  if lobby.game.game_type == 'Visit Train':
    content += '\n**🚆 Stops:**'
    content += lobby.get_party_list(numbered=True, include_island=True)
  else:
    content += f'\nIsland: **{lobby.island.name}**!'
    content += '\n**Party:**'
    content += lobby.get_party_list(numbered=False, include_island=False)
  json = {
    'content': content,
    'components': components,
    'flags': 4 # supress embeds
  }
  reply_response = requests.post(url, json=json, headers=headers)
  reply_response.raise_for_status()
