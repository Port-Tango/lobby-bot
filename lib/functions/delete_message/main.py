import functions_framework
from messages import delete_message
from pydantic import BaseModel, ValidationError

class DeleteMessageRequest(BaseModel):
  channel_id: str
  message_id: str

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    config = DeleteMessageRequest(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  delete_message(channel_id=config.channel_id, message_id=config.message_id)

  return "OK", 200
