import requests
from firebase_admin import firestore
import functions_framework
from database import Island

ISLANDS_ENDPOINT = 'https://api.niftyisland.com/api/v2/islands'

db = firestore.client()
collection_ref = db.collection('islands')

def pull_islands_batch(limit: int, offset: int) -> dict:
  try:
    params = {'limit': limit, 'offset': offset}
    response = requests.get(ISLANDS_ENDPOINT, params=params)
    response.raise_for_status()
    return response.json()
  except Exception as error:
    print(f"Error fetching islands with offset {offset}: {error}")
    return {}

def validate_islands(islands: list[dict]) -> list[dict]:
  return [
    Island(**{
      'id': island['valueId'],
      'name': island['name'],
      'url': f"https://niftyis.land/{island['owner']['username']}/{island['deeplinkIndex']}"
    }).dict() for island in islands if island['bloomsPlaced'] >= 25
  ]

def process_and_write_batch(islands: list[dict]):
  validated_islands = validate_islands(islands)
  if validated_islands:
    batch_write_to_firestore(collection_ref, validated_islands)

def pull_all_islands():
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
      process_and_write_batch(islands)

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

@functions_framework.http
def handler(request):
  print(request)
  pull_all_islands()
  return "OK", 200
