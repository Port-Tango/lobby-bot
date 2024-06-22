import requests

ISLANDS_ENDPOINT = 'https://api.niftyisland.com/api/v2/islands'

def get_islands(params)->list[dict]:
  response = requests.get(ISLANDS_ENDPOINT, params=params)
  response.raise_for_status()
  islands = response.json()['items']
  choices = [
    {
      'name': f"{island['name']} | 🟢 {island['playerCount']} online",
      'value': island['valueId']
    }
    for island in islands
  ]
  return choices

def generate_island_choices(query)->list[dict]:
  base_params = {"limit":"10","order":"active"}
  if not query or query == "":
    choices = get_islands(params=base_params)
    choices.insert(0, {"name": "🏠 My Island", "value": "my"})
    return choices
  choices = get_islands(params={**base_params,"order":"active","search":query})
  print(choices)
  return choices
