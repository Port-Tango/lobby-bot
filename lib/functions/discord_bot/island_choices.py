from firebase_admin import firestore

db = firestore.client()
islands_collection_ref = db.collection('islands')
top_10_document_ref = db.collection('top_10_islands').document('latest')

def get_top_10_islands():
  try:
    top_10_doc = top_10_document_ref.get()
    if not top_10_doc.exists:
      print("No top 10 islands document found")
      return []
    islands = top_10_doc.to_dict().get('islands', [])
    return islands
  except Exception as error:
    print(f"Error fetching top 10 islands: {error}")
    return []

def search_islands(query_str: str):
  try:
    island_results = islands_collection_ref.where(
      'search_tokens',
      'array_contains',
      query_str.lower()
    ).stream()
    islands = [doc.to_dict() for doc in island_results]
    islands = sorted(islands, key=lambda island: island.get('favorited_count', 0), reverse=True)
    return islands
  except Exception as error:
    print(f"Error searching islands: {error}")
    return []

def format_choices(
  islands: list[dict],
  include_owner: bool = True,
  include_player_count: bool = False,
  include_favorited_count: bool = False,
  include_self: bool = True
):
  choices = []
  for island in islands:
    name = island['name']
    if include_owner:
      name += f" | 👤 {island['owner']['nickname']}"
    if include_player_count:
      name += f" | 🟢 {island['player_count']} online"
    if include_favorited_count:
      name += f" | ⭐ {island['favorited_count']} favorited"
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
    choices = format_choices(islands, include_player_count=True)
    return choices
  islands = search_islands(query)
  choices = format_choices(islands, include_player_count=False, include_favorited_count=True)
  return choices
