import os
from enum import Enum
from typing import Optional
import requests
from pydantic import BaseModel

BOT_APP_ID = os.getenv('BOT_APP_ID')
BASE_URL = 'https://discord.com/api/v10'

class ResponseType(Enum):
  PONG = 1
  DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5
  DEFERRED_UPDATE_MESSAGE = 6

def get_message_id(interaction_token: str) -> str:
  url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{interaction_token}/messages/@original'
  initial_response = requests.get(url)
  initial_response_json = initial_response.json()
  return initial_response_json['id']

class Channel(BaseModel):
  id: str
  name: str

class Interaction(BaseModel):
  id: str
  token: str
  channel: Channel
  acked: Optional[bool] = False
  message_id: Optional[str] = None

  def get_message_id(self):
    url = f'{BASE_URL}/webhooks/{BOT_APP_ID}/{self.token}/messages/@original'
    if not self.acked:
      raise ValueError('Interaction must be acknowledged before getting message ID')
    initial_response = requests.get(url)
    initial_response_json = initial_response.json()
    self.message_id = initial_response_json['id']

  def ack(self, response_type, ephemeral=False):
    url = f'{BASE_URL}/interactions/{self.id}/{self.token}/callback'

    json = {
      'type': response_type,
      'data': {
        'tts': False
      }
    }

    if ephemeral:
      json['data']['flags'] = 64

    reply_response = requests.post(url, json=json)
    reply_response.raise_for_status()
    self.acked = True
    self.get_message_id()

  def ack_application_command(self, ephemeral=False):
    self.ack(
      response_type=ResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value,
      ephemeral=ephemeral
    )

  def ack_message_component(self, ephemeral=False):
    self.ack(
      response_type=ResponseType.DEFERRED_UPDATE_MESSAGE.value,
      ephemeral=ephemeral
    )

  class Config:
    validate_assignment = True
