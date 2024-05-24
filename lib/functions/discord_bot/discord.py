import os
from typing import Optional
from enum import Enum
import requests
from flask import abort
from pydantic import BaseModel
from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey
from database import Lobby
from utils import wrap_error_message, user_mentions_single_line, user_mentions_bulleted_list
from messages import delayed_delete_message

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_PUBLIC_KEY = os.getenv('BOT_PUBLIC_KEY')
BOT_APP_ID = os.getenv('BOT_APP_ID')
LOBBY_CHANNEL = os.getenv('LOBBY_CHANNEL')
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

class ResponseType(Enum):
  PONG = 1
  DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
  DEFERRED_UPDATE_MESSAGE = 6

class ChannelType(Enum):
  PUBLIC_THREAD	= 11

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

def get_message_id(interaction_token: str) -> str:
  url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{interaction_token}/messages/@original'
  initial_response = requests.get(url)
  initial_response_json = initial_response.json()
  return initial_response_json['id']

class Interaction(BaseModel):
  id: str
  token: str
  acked: Optional[bool] = False
  message_id: Optional[str] = None

  def get_message_id(self):
    url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{self.token}/messages/@original'
    if not self.acked:
      raise ValueError('Interaction must be acknowledged before getting message ID')
    initial_response = requests.get(url)
    initial_response_json = initial_response.json()
    self.message_id = initial_response_json['id']

  def ack(self, response_type):
    url = f'{BASE_URL}/interactions/{self.id}/{self.token}/callback'

    json = {
      'type': response_type,
      'data': {
        'tts': False
      }
    }

    reply_response = requests.post(url, json=json)
    reply_response.raise_for_status()
    self.acked = True
    self.get_message_id()

  class Config:
    validate_assignment = True

def bot_reply_response(interaction: Interaction, json: dict) -> str:
  url = f'{BASE_URL}/channels/{LOBBY_CHANNEL}/messages'
  json = {**json,**{'message_reference': {'message_id': interaction.message_id}}}
  reply_response = requests.post(url, json=json, headers=headers)
  reply_response.raise_for_status()
  reply_response_json = reply_response.json()
  return reply_response_json['id']

def bot_error_reply_response(
    interaction: Interaction,
    error_message: str,
    mention_user_ids: Optional[list] = None
  ):
  json={'content': error_message}
  if mention_user_ids:
    mentions = user_mentions_single_line(mention_user_ids)
    json['content'] += f'\n{mentions}'
  message_id = bot_reply_response(interaction=interaction, json=json)
  delayed_delete_message(message_id, delay_in_seconds=20)

def bot_error_response(interaction: Interaction, error_message: str):
  url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{interaction.token}/messages/@original'
  json = {'content': error_message}
  reply_response = requests.patch(url, json=json)
  reply_response.raise_for_status()
  delayed_delete_message(message_id=interaction.message_id, delay_in_seconds=20)

def validate_application_command(data, interaction):
  if data['channel']['type'] == ChannelType.PUBLIC_THREAD.value:
    bot_error_response(
      interaction=interaction,
      error_message=wrap_error_message(DiscordErrorType.COMMAND_IN_THREAD.value)
    )
    abort(400, DiscordErrorType.COMMAND_IN_THREAD.value)

  if data['channel_id'] != LOBBY_CHANNEL:
    bot_error_response(
      interaction=interaction,
      error_message=wrap_error_message(DiscordErrorType.INVALID_CHANNEL.value)
    )
    abort(400, DiscordErrorType.INVALID_CHANNEL.value)

  if data['data']['name'] != 'lobby':
    bot_error_response(
      interaction=interaction,
      error_message=wrap_error_message(DiscordErrorType.INVALID_COMMAND.value)
    )
    abort(400, DiscordErrorType.INVALID_COMMAND.value)

  if data['data']['options'][0]['name'] != 'create':
    bot_error_response(
      interaction=interaction,
      error_message=wrap_error_message(DiscordErrorType.INVALID_SUBCOMMAND_GROUP.value)
    )
    abort(400, DiscordErrorType.INVALID_SUBCOMMAND_GROUP.value)

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
  participants = '\n* '.join(lobby.player_names)
  content = f'A new **{lobby.game.game_type}** lobby'
  content += f' has been created for **{lobby.island.name}**!'
  content += '\n**Players in lobby:** '
  content += f'({lobby.player_count}/{lobby.game.min_players})'
  content += f'\n* {participants}'
  content += '\n**Lobby status:**\n```diff\n+ OPEN\n```'
  json = {'content': content, 'components': components}
  reply_response = requests.patch(url, json=json)
  reply_response.raise_for_status()

def bot_party_notification(lobby: Lobby):
  url = f'{BASE_URL}/channels/{PARTY_CHANNEL}/messages'
  components = [
    {
      'type': 1,
      'components': [
        {
          'type': 2,
          'label': 'Join Game Island',
          'style': 5,
          'url': lobby.island.url
        }
      ]
    }
  ]
  mentions = user_mentions_bulleted_list(lobby.player_ids)
  content = f'A new **{lobby.game.game_type}** party of {lobby.game.min_players}'
  content += ' players has been matched!'
  content += f'\nIsland: **{lobby.island.name}**!'
  content += f'\n**Party:** {mentions}'
  json = {'content': content,'components': components}
  reply_response = requests.post(url, json=json, headers=headers)
  reply_response.raise_for_status()
