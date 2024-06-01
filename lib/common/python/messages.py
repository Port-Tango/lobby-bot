import os
from typing import Optional
import requests
from cloud_tasks import create_http_task
from interactions import Interaction

REGION = os.getenv('REGION')
PROJECT_ID = os.getenv('PROJECT_ID')
BOT_TOKEN = os.getenv('BOT_TOKEN')
BASE_URL = 'https://discord.com/api/v10/channels'

headers = {
  'Authorization': f'Bot {BOT_TOKEN}',
  'Content-Type': 'application/json'
}

def get_messages(channel_id):
  url = f'{BASE_URL}/{channel_id}/messages'
  params = {'limit': 100}
  response = requests.get(url, params=params, headers=headers)
  response.raise_for_status()
  messages = response.json()
  return messages

def delete_message(channel_id, message_id):
  url = f'{BASE_URL}/{channel_id}/messages/{message_id}'
  response = requests.delete(url, headers=headers)
  response.raise_for_status()

def bulk_delete_messages(channel_id, messages):
  url = f'{BASE_URL}/{channel_id}/messages/bulk-delete'
  payload = {"messages": messages}
  response = requests.post(url, headers=headers, json=payload)
  response.raise_for_status()

def delayed_delete_ephemeral_message(
  interaction: Interaction,
  delay_in_seconds: int,
  message_id: Optional[str] = None
):
  url=f'https://{REGION}-{PROJECT_ID}.cloudfunctions.net/delete_ephemeral_message'
  create_http_task(
    queue='delayed-task-queue',
    url=url,
    json_payload={
      'interaction': interaction.dict(),
      'message_id': message_id
    },
    delay_in_seconds=delay_in_seconds
  )
