import os
import random
from typing import Optional, List, Dict
from enum import Enum
import requests
import firebase_admin
from firebase_admin import firestore
from pydantic import BaseModel, validator
from utils import now_iso_str, wrap_error_message
from cloud_tasks import create_http_task
from messages import delete_message

REGION = os.getenv('REGION')
PROJECT_ID = os.getenv('PROJECT_ID')
GAME_TYPES = ['FFA DM', 'CTF', 'Spy Hunt', 'Zombies', 'Visit Train']

class LobbyErrorType(Enum):
  PLAYER_IN_OTHER_LOBBY = 'you are in another open lobby'
  NO_IN_GAME_USERNAME = 'you have not yet set your in-game username using "/lobby set username"'
  NO_ISLAND = 'you have not yet set your island using "/lobby set island"'
  GAME_TYPE_EXISTS = 'an open lobby already exists for game type'

class LobbyActionType(Enum):
  CREATE = 'create'
  JOIN = 'join'

app = firebase_admin.initialize_app()
db = firestore.client()

class Game(BaseModel):
  game_type: str
  is_featured: Optional[bool] = None
  min_players: Optional[int] = None

  @validator('game_type', always=True, pre=True)
  def validate_type(cls, game_type):
    if game_type not in GAME_TYPES:
      raise ValueError('Invalid game type')
    return game_type

  class Config:
    validate_assignment = True

class Island(BaseModel):
  id: str
  name: Optional[str] = None
  games: List[Game] = []
  url: Optional[str] = None

  class Config:
    validate_assignment = True

  def get_url(self):
    url = f'https://api.niftyisland.com/api/islands/{self.id}/preview'
    response = requests.get(url)
    data = response.json()
    deep_link_index = data['deeplinkIndex']
    owner = data['owner']['username']
    self.name = data['name']
    self.url = f'https://niftyis.land/{owner}/{deep_link_index}'

class Player(BaseModel):
  id: str
  name: str
  username: str = None
  island: Optional[Island] = None

  class Config:
    validate_assignment = True

  def create(self):
    db.collection('players').document(self.id).set(self.dict())

  def update(self):
    db.collection('players').document(self.id).set(self.dict(), merge=True)

  def set_name(self, name: str):
    self.name = name
    self.update()

  def set_username(self, username: str):
    self.username = username
    self.update()

  def set_island(self, island: Island):
    self.island = island
    self.update()

def get_player(player_id: str) -> Optional[Player]:
  doc_ref = db.collection('players').document(player_id)
  doc = doc_ref.get()
  if not doc.exists:
    return None
  return Player(**doc.to_dict())

class Lobby(BaseModel):
  id: str
  channel_id: str
  creation_time: str = now_iso_str()
  creator: Player
  game: Game
  island: Optional[Island] = None
  status: str
  players: list[Player]
  player_count: Optional[int] = None
  player_ids: Optional[list[str]] = None
  player_names: Optional[list[str]] = None
  player_usernames: Optional[list[Optional[str]]] = None
  player_island_urls: Optional[list[Optional[str]]] = None

  @validator('status', always=True, pre=True)
  def validate_status(cls, status, values):
    if 'status' in values and values['status']:
      if values['status'] not in ['open', 'closed']:
        raise ValueError('Invalid status')
    return status

  def update_player_stats(self):
    self.player_count = len(self.players)
    self.player_ids = [player.id for player in self.players]
    self.player_names = [player.name for player in self.players]
    self.player_usernames = [
      player.username if player.username else None
      for player in self.players
    ]
    self.player_island_urls = [
      player.island.url if player.island else None
      for player in self.players
    ]

  def create(self):
    self.update_player_stats()
    db.collection('lobbies').document(self.id).set(self.dict())

  def update(self):
    self.update_player_stats()
    db.collection('lobbies').document(self.id).set(self.dict(), merge=True)

  def close(self):
    self.status = 'closed'
    self.update()
    delete_message(channel_id=self.channel_id, message_id=self.id)

  def add_player(self, player: Player):
    if player not in self.players:
      self.players.append(player)
      self.update()

  def remove_player(self, player: Player):
    if player in self.players:
      self.players.remove(player)
      self.update()

  def randomize_players(self):
    random.shuffle(self.players)
    self.update()

  def get_party_list(
    self,
    numbered: Optional[bool] = False,
    include_island: Optional[bool] = False
  ):
    list_str = ''
    if numbered:
      for i, player in enumerate(self.players, start=1):
        list_str += f'\n{i}. <@{player.id}>'
        if player.username:
          list_str += f' | 👤: **{player.username}**'
        if include_island and player.island:
          list_str += f' | 🏝️: [{player.island.name}]({player.island.url})'
    else:
      for player in self.players:
        list_str += f'\n* <@{player.id}>'
        if player.username:
          list_str += f' | 👤: **{player.username}**'
        if include_island and player.island:
          list_str += f' | 🏝️: [{player.island.name}]({player.island.url})'
    return list_str

  class Config:
    validate_assignment = True

def get_lobby(lobby_id: str) -> Lobby:
  doc_ref = db.collection('lobbies').document(lobby_id)
  doc = doc_ref.get()
  if not doc.exists:
    raise ValueError('Invalid lobby_id: {lobby_id}')
  return Lobby(**doc.to_dict())

def get_open_lobbies() -> List[Lobby]:
  lobbies = []
  docs = db.collection('lobbies').where(field_path='status', op_string='==', value='open').stream()
  for doc in docs:
    lobbies.append(Lobby(**doc.to_dict()))
  return lobbies

def get_lobby_players(lobbies: List[Lobby], exclusion_lobby: Optional[Lobby] = None) -> List[str]:
  player_ids = []
  for lobby in lobbies:
    if exclusion_lobby and lobby.id == exclusion_lobby.id:
      continue
    player_ids.extend(lobby.player_ids)
  return list(set(player_ids))

def get_lobby_game_types(lobbies: List[Lobby]) -> List[str]:
  game_types = []
  for lobby in lobbies:
    game_types.append(lobby.game.game_type)
  return list(set(game_types))

def get_lobby_error_message(
  player: Player,
  game: Game,
  island: Optional[Island],
  error_type: LobbyErrorType,
  action: LobbyActionType
) -> str:
  message = f'You tried to {action.value} a lobby for {game.game_type}'
  if island:
    message += f' on {island.name}'
  message += f'but were denied because {error_type.value}.'
  if error_type not in [LobbyErrorType.NO_IN_GAME_USERNAME, LobbyErrorType.NO_ISLAND]:
    message += f' Shame on you, {player.name}! Shame! Shame! Shame!'
  return wrap_error_message(message)

def get_lobby_creation_eligibility(player: Player, game: Game, island: Island) -> Dict:
  if not player.username:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=game,
        island=island,
        error_type=LobbyErrorType.NO_IN_GAME_USERNAME,
        action=LobbyActionType.CREATE
      )
    }

  if game.game_type == 'Visit Train' and not player.island:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=game,
        island=island,
        error_type=LobbyErrorType.NO_ISLAND,
        action=LobbyActionType.CREATE
      )
    }

  open_lobbies = get_open_lobbies()
  player_ids = get_lobby_players(open_lobbies)
  if player.id in player_ids:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=game,
        island=island,
        error_type=LobbyErrorType.PLAYER_IN_OTHER_LOBBY,
        action=LobbyActionType.CREATE
      )
    }

  game_types = get_lobby_game_types(open_lobbies)
  if game.game_type in game_types:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=game,
        island=island,
        error_type=LobbyErrorType.GAME_TYPE_EXISTS,
        action=LobbyActionType.CREATE
      )
    }

  return {'eligibility': True}

def get_player_join_eligibility(player: Player, lobby: Lobby) -> Dict:
  if not player.username:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=lobby.game,
        island=lobby.island,
        error_type=LobbyErrorType.NO_IN_GAME_USERNAME,
        action=LobbyActionType.JOIN
      )
    }

  if lobby.game.game_type == 'Visit Train' and not player.island:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=lobby.game,
        island=lobby.island,
        error_type=LobbyErrorType.NO_ISLAND,
        action=LobbyActionType.CREATE
      )
    }

  open_lobbies = get_open_lobbies()
  player_ids = get_lobby_players(lobbies=open_lobbies, exclusion_lobby=lobby)
  if player.id in player_ids:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        game=lobby.game,
        island=lobby.island,
        error_type=LobbyErrorType.PLAYER_IN_OTHER_LOBBY,
        action=LobbyActionType.JOIN
      )
    }

  return {'eligibility': True}

def delayed_close_delete_lobby(
  channel_id: str,
  lobby_id: str,
  delay_in_seconds: int,
  only_if_open: Optional[bool] = False
):
  url=f'https://{REGION}-{PROJECT_ID}.cloudfunctions.net/close_delete_lobby'
  create_http_task(
    queue='delayed-task-queue',
    url=url,
    json_payload={'channel_id': channel_id, 'lobby_id': lobby_id, 'only_if_open': only_if_open},
    delay_in_seconds=delay_in_seconds
  )
