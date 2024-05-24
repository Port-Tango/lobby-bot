from typing import Optional
import functions_framework
from database import get_lobby
from messages import delete_message
from pydantic import BaseModel, ValidationError

class CloseDeleteLobbyRequest(BaseModel):
  lobby_id: str
  only_if_open: Optional[bool] = False

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    config = CloseDeleteLobbyRequest(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  lobby = get_lobby(lobby_id=config.lobby_id)

  if config.only_if_open and lobby.status != 'open':
    return "OK", 200

  lobby.close()
  delete_message(message_id=config.lobby_id)

  return "OK", 200
