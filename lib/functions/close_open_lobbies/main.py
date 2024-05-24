import functions_framework
from database import get_open_lobbies
from pydantic import BaseModel, ValidationError
from utils import calc_age_seconds

class CloseOpenLobbiesRequest(BaseModel):
  age_threshold_seconds: int

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    config = CloseOpenLobbiesRequest(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  lobbies = get_open_lobbies()

  for lobby in lobbies:
    age_seconds = calc_age_seconds(lobby.creation_time)
    if age_seconds > config.age_threshold_seconds:
      lobby.close()

  return "OK", 200
