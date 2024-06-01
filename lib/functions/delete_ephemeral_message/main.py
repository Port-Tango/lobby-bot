import os
from typing import Optional
import requests
import functions_framework
from pydantic import ValidationError, BaseModel
from discord import Interaction

class DeleteEphemeralMessageConfig(BaseModel):
  interaction: Interaction
  message_id: Optional[str] = None

  class Config:
    validate_assignment = True

BOT_APP_ID = os.getenv('BOT_APP_ID')
BASE_URL = f'https://discord.com/api/v10/webhooks/{BOT_APP_ID}'

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    config = DeleteEphemeralMessageConfig(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  if config.message_id:
    response = requests.delete(
      url=f'{BASE_URL}/{config.interaction.token}/messages/{config.message_id}'
    )
  else:
    response = requests.delete(url=f'{BASE_URL}/{config.interaction.token}/messages/@original')

  response.raise_for_status()

  return "OK", 200
