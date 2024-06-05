from typing import Optional
import functions_framework
from database import get_lobby
from pydantic import BaseModel, ValidationError

class CloseDeleteLobbyRequest(BaseModel):
  channel_id: str
  lobby_id: str
  only_if_open: Optional[bool] = False

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    config = CloseDeleteLobbyRequest(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  lobby = get_lobby(message_id=config.lobby_id)

  if config.only_if_open and lobby.status != 'open':
    return "OK", 200

  lobby.close()
  return "OK", 200
