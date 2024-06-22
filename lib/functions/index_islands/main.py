import requests
from firebase_admin import firestore
from flask import jsonify
import functions_framework
from pydantic import BaseModel, validator, ValidationError
from database import Island

ISLANDS_ENDPOINT = 'https://api.niftyisland.com/api/v2/islands'

db = firestore.client()
collection_ref = db.collection('islands')
top_10_collection_ref = db.collection('top_10_islands')

class IslandIndexRequest(BaseModel):
  request_type: str

  @validator('request_type')
  def validate_type(cls, request_type):
    if request_type not in ['all', 'top']:
      raise ValidationError('Invalid request type')
    return request_type

def pull_islands_batch(limit: int, offset: int, order: str = None) -> dict:
  try:
    params = {'limit': limit, 'offset': offset}
    if order:
      params['order'] = order
    response = requests.get(ISLANDS_ENDPOINT, params=params)
    response.raise_for_status()
    return response.json()
  except Exception as error:
    print(f"Error fetching islands with offset {offset}: {error}")
    return {}

# Function to generate prefixes
def generate_search_tokens(name: str) -> list[str]:
  tokens = name.lower().split()  # Convert to lowercase and split
  prefixes = []
  for token in tokens:
    for i in range(len(token)):
      prefixes.append(token[:i+1])  # Add all prefixes up to the current character'
  return tokens + prefixes

def validate_islands(islands: list[dict]) -> list[dict]:
  return [
    Island(**{
      'id': island['valueId'],
      'name': island['name'],
      'search_tokens': generate_search_tokens(name=island['name']),
      'url': f"https://niftyis.land/{island['owner']['username']}/{island['deeplinkIndex']}",
      'player_count': island['playerCount'],
      'owner': island['owner'],
      'favorited_count': island['favoritedCount']
    }).dict() for island in islands if island['bloomsPlaced'] >= 25
  ]

def process_and_write_batch(ref: str, islands: list[dict]):
  validated_islands = validate_islands(islands=islands)
  if validated_islands:
    batch_write_to_firestore(ref, validated_islands)

def index_all_islands():
  try:
    # Fetch the first batch to get the total count
    initial_response = pull_islands_batch(1, 0)
    total = initial_response.get('total', 0)
    print(f"Total islands: {total}")

    for offset in range(0, total, 500):
      batch_response = pull_islands_batch(500, offset)
      islands = batch_response.get('items', [])
      print(f"Fetched {offset + len(islands)} / {total} islands so far")

      # Process and write the batch
      process_and_write_batch(ref=collection_ref, islands=islands)

  except Exception as error:
    print(f"Error during data fetch and processing: {error}")

def batch_write_to_firestore(collection, items):
  try:
    batch = db.batch()
    for item in items:
      doc_ref = collection.document(item['id'])
      batch.set(doc_ref, item)
    batch.commit()
    print(f"Successfully wrote {len(items)} items to Firestore")
  except Exception as error:
    print(f"Error writing to Firestore: {error}")

def get_existing_top_10_ids() -> set:
  try:
    snapshot = top_10_collection_ref.get()
    return {doc.id for doc in snapshot}
  except Exception as error:
    print(f"Error fetching existing top 10 island IDs: {error}")
    return set()

def index_top_10_islands():
  try:
    current_top_10_ids = get_existing_top_10_ids()
    top_10_islands_response = pull_islands_batch(limit=10, offset=0, order='active')
    top_10_islands = top_10_islands_response.get('items', [])
    new_top_10_ids = {island['id'] for island in top_10_islands}
    islands_to_delete = current_top_10_ids - new_top_10_ids
    process_and_write_batch(ref=top_10_collection_ref, islands=top_10_islands)
    batch_delete = db.batch()
    for island_id in islands_to_delete:
      doc_ref = top_10_collection_ref.document(island_id)
      batch_delete.delete(doc_ref)
    batch_delete.commit()
  except Exception as error:
    print(f"Error fetching and storing top 10 islands: {error}")

@functions_framework.http
def handler(request):
  request_json = request.get_json(silent=True)
  try:
    index_request = IslandIndexRequest(**request_json)
  except ValidationError as validation_error:
    return f'Problem parsing input. {validation_error}', 400

  if index_request.request_type == 'all':
    index_all_islands()
  else:
    index_top_10_islands()
  return jsonify({'message': 'Indexing complete', 'request_type': index_request.request_type})
