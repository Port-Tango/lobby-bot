import os
import yaml
import requests
import functions_framework
from database import Island

BOT_TOKEN = os.getenv('BOT_TOKEN')
BOT_APP_ID = os.getenv('BOT_APP_ID')

url = f"https://discord.com/api/v10/applications/{BOT_APP_ID}/commands"

headers = {
  "Authorization": f"Bot {BOT_TOKEN}",
  "Content-Type": "application/json"
}

with open('islands.yaml', 'r', encoding='utf-8') as file:
  islands_config = yaml.safe_load(file)

with open('lobby_create.yaml', 'r', encoding='utf-8') as file:
  lobby_create_config = yaml.safe_load(file)

with open('lobby_set.yaml', 'r', encoding='utf-8') as file:
  set_subcommand_group = yaml.safe_load(file)

game_modes = lobby_create_config['game_modes']

islands = [Island(**island) for island in islands_config]

def create_island_choices(game_type):
  choices = []
  for island in islands:
    for game in island.games:
      if game.game_type == game_type and game.is_featured:
        choices.append({"name": island.name, "value": island.id})
  return choices

def create_player_count_choices(min_players, max_players, step):
  return [{"name": str(i), "value": i} for i in range(min_players, max_players + 1, step)]

commands = [
  {
    "name": lobby_create_config['command'],
    "description": "Main command to summon LobbyBot",
    "options": [set_subcommand_group]
  }
]

create_subcommand_group = {
  "name": lobby_create_config['subcommand_group'],
  "type": 2,  # 2 is for subcommand groups
  "description": "Create a new lobby",
  "options": []
}

for subcommand_name, mode_info in game_modes.items():
  island_choices = create_island_choices(mode_info['type'])
  if island_choices:
    subcommand = {
      "name": subcommand_name,
      "type": 1,  # 1 is for subcommands
      "description": f"Creates a matchmaking lobby for {mode_info['type']} game mode",
      "options": [
        {
          "name": "island",
          "description": "The name of island where the game will be hosted",
          "type": 3,  # 3 is for string options
          "required": True,
          "choices": island_choices
        },
        {
          "name": "players",
          "description": "Amount of players. Lobby will auto-close after this threshold is met",
          "type": 4,  # 4 is for integer options
          "required": True,
          "choices": create_player_count_choices(
            mode_info['min_players'], mode_info['max_players'], mode_info['player_count_step']
          )
        }
      ]
    }
    create_subcommand_group['options'].append(subcommand)

commands[0]['options'].append(create_subcommand_group)
print(commands)

@functions_framework.http
def handler(request):
  print(request)
  for command in commands:
    response = requests.post(url, headers=headers, json=command)
    response.raise_for_status()
  return 'OK', 200
