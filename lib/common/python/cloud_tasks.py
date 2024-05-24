import os
import json
import datetime
from typing import Dict, Optional
from google.cloud import tasks_v2
from google.protobuf import timestamp_pb2
import google.auth.transport.requests
import google.oauth2.id_token

REGION = os.getenv('REGION')
PROJECT_ID = os.getenv('PROJECT_ID')

auth_req = google.auth.transport.requests.Request()
client = tasks_v2.CloudTasksClient()

def create_http_task(
  queue: str,
  url: str,
  json_payload: Dict,
  delay_in_seconds: Optional[int] = None
) -> tasks_v2.Task:
  """Create an HTTP POST task with a JSON payload.
  Args:
    queue: The ID of the queue to add the task to.
    url: The target URL of the task.
    json_payload: The JSON payload to send.
    delay_in_seconds: The delay in seconds before the task should be executed.
  Returns:
    The newly created task.
  """

  token = google.oauth2.id_token.fetch_id_token(auth_req, url)

  headers = {
    "Content-type": "application/json",
    "Authorization": f"Bearer {token}"
  }

  task = tasks_v2.Task(
    http_request=tasks_v2.HttpRequest(
      http_method=tasks_v2.HttpMethod.POST,
      url=url,
      body=json.dumps(json_payload).encode(),
      headers=headers,
    ),
  )

  if delay_in_seconds:
    schedule_time = timestamp_pb2.Timestamp() # pylint: disable=no-member
    schedule_time.FromDatetime(
      datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=delay_in_seconds)
    )
    task.schedule_time = schedule_time

  return client.create_task(
    tasks_v2.CreateTaskRequest(
      parent=client.queue_path(PROJECT_ID, REGION, queue),
      task=task,
    )
  )
