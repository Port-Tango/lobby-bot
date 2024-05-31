import os
from typing import Optional, List, Dict
from enum import Enum
import requests
import firebase_admin
from firebase_admin import firestore
from pydantic import BaseModel, validator, ValidationError
from utils import now_iso_str, wrap_error_message
from cloud_tasks import create_http_task
from messages import delete_message

REGION = os.getenv('REGION')
PROJECT_ID = os.getenv('PROJECT_ID')
GAME_TYPES = ['FFA DM', 'CTF', 'Spy Hunt', 'Zombies']

class LobbyErrorType(Enum):
  PLAYER_IN_OTHER_LOBBY = 'player is in another open lobby'
  GAME_TYPE_EXISTS = 'an open lobby already exists for game type'

class LobbyActionType(Enum):
  CREATE = 'create'
  JOIN = 'join'

class Player(BaseModel):
  id: str
  name: str

  class Config:
    validate_assignment = True

app = firebase_admin.initialize_app()
db = firestore.client()

class Game(BaseModel):
  game_type: str
  is_featured: Optional[bool] = None
  min_players: Optional[int] = None

  @validator('game_type', always=True, pre=True)
  def validate_type(cls, game_type):
    if game_type not in GAME_TYPES:
      raise ValidationError('Invalid game type')
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


class Lobby(BaseModel):
  id: str
  creation_time: str = now_iso_str()
  creator: Player
  game: Game
  island: Island
  status: str
  players: list[Player]
  player_count: Optional[int] = None
  player_ids: Optional[list[str]] = None
  player_names: Optional[list[str]] = None

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

  def create(self):
    self.update_player_stats()
    db.collection('lobbies').document(self.id).set(self.dict())

  def update(self):
    self.update_player_stats()
    db.collection('lobbies').document(self.id).set(self.dict(), merge=True)

  def close(self):
    self.status = 'closed'
    self.update()
    delete_message(message_id=self.id)

  def add_player(self, player: Player):
    if player not in self.players:
      self.players.append(player)
      self.update()

  def remove_player(self, player: Player):
    if player in self.players:
      self.players.remove(player)
      self.update()

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
  lobby: Lobby,
  error_type: LobbyErrorType,
  action: LobbyActionType
) -> str:
  message = f'{player.name} tried to {action.value} a lobby for {lobby.game.game_type}'
  message += f' on {lobby.island.name} but was denied because {error_type.value}.'
  message += f' Shame on {player.name}! Shame! Shame! Shame!'
  return wrap_error_message(message)

def get_lobby_creation_eligibility(lobby: Lobby) -> Dict:
  open_lobbies = get_open_lobbies()

  player_ids = get_lobby_players(open_lobbies)
  player = lobby.creator
  if player.id in player_ids:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        lobby=lobby,
        error_type=LobbyErrorType.PLAYER_IN_OTHER_LOBBY,
        action=LobbyActionType.CREATE
      )
    }

  game_types = get_lobby_game_types(open_lobbies)
  if lobby.game.game_type in game_types:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        lobby=lobby,
        error_type=LobbyErrorType.GAME_TYPE_EXISTS,
        action=LobbyActionType.CREATE
      )
    }

  return {'eligibility': True}

def get_player_join_eligibility(player: Player, lobby: Lobby) -> Dict:
  open_lobbies = get_open_lobbies()

  player_ids = get_lobby_players(lobbies=open_lobbies, exclusion_lobby=lobby)
  if player.id in player_ids:
    return {
      'eligibility': False,
      'error_message': get_lobby_error_message(
        player=player,
        lobby=lobby,
        error_type=LobbyErrorType.PLAYER_IN_OTHER_LOBBY,
        action=LobbyActionType.JOIN
      )
    }

  return {'eligibility': True}

def delayed_close_delete_lobby(
  lobby_id: str,
  delay_in_seconds: int,
  only_if_open: Optional[bool] = False
):
  url=f'https://{REGION}-{PROJECT_ID}.cloudfunctions.net/close_delete_lobby'
  create_http_task(
    queue='delayed-task-queue',
    url=url,
    json_payload={'lobby_id': lobby_id, 'only_if_open': only_if_open},
    delay_in_seconds=delay_in_seconds
  )
