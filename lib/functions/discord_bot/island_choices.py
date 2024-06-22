from firebase_admin import firestore

db = firestore.client()
islands_collection_ref = db.collection('islands')
top_10_islands_collection_ref = db.collection('top_10_islands')

def get_top_10_islands():
  try:
    top_10_islands = top_10_islands_collection_ref.stream()
    top_10_islands = sorted(
      top_10_islands,
      key=lambda island: (
        -island.to_dict()['player_count'],
        -island.to_dict()['favorited_count']
      )
    )
    islands = [doc.to_dict() for doc in top_10_islands]
    return islands
  except Exception as error:
    print(f"Error fetching top 10 islands: {error}")
    return []

def search_islands(query_str: str):
  query_tokens = query_str.lower().split()
  try:
    island_results = islands_collection_ref.where(
      'search_tokens',
      'array_contains_any',
      query_tokens
    ).stream()
    islands = [doc.to_dict() for doc in island_results]
    return islands
  except Exception as error:
    print(f"Error searching islands: {error}")
    return []

def format_choices(
  islands: list[dict],
  include_player_count: bool = False,
  include_self: bool = False
):
  choices = []
  for island in islands:
    name = island['name']
    if include_player_count:
      name = f"{name} | 👤 {island['owner']['nickname']} | 🟢 {island['player_count']} online"
    choices.append({
      'name': name,
      'value': island['id']
    })
  if include_self:
    choices.insert(0, {"name": "🏠 My Island", "value": "my"})
  return choices

def generate_island_choices(query:str)->list[dict]:
  if not query or query == "":
    islands = get_top_10_islands()
    choices = format_choices(islands, include_player_count=True, include_self=True)
    return choices
  islands = search_islands(query)
  choices = format_choices(islands, include_player_count=False, include_self=True)
  return choices
