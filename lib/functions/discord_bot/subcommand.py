import os
from typing import Optional, Any
from discord import (
  bot_lobby_response,
  bot_followup_response,
  DiscordErrorType
)
from database import (
  get_lobby_creation_eligibility,
  delayed_close_delete_lobby,
  GAME_TYPES,
  Game,
  Island,
  Player,
  Lobby
)
from flask import abort
from pydantic import BaseModel, validator
from utils import now_iso_str, wrap_error_message, wrap_success_message
from interactions import Interaction, ResponseType

LOBBY_CHANNEL = os.getenv('LOBBY_CHANNEL')

subcommand_game_type_map = {
  'ctf': 'CTF',
  'spy_hunt': 'Spy Hunt',
  'zombies': 'Zombies',
  'dm_ffa': 'FFA DM',
  'train': 'Visit Train'
}

def handle_subcommand_error(interaction: Interaction, error: DiscordErrorType):
  interaction.ack(
    response_type=ResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value,
    ephemeral=True
  )
  bot_followup_response(
    interaction=interaction,
    ephemeral=True,
    json={'content': wrap_error_message(error.value)}
  )
  abort(400, error.value)

class Subcommand(BaseModel):
  interaction: Interaction
  command: str
  subcommand_group: str
  subcommand: str
  param1: Any
  param2: Optional[Any] = None
  island_id: Optional[str] = None
  min_players: Optional[int] = None
  username: Optional[str] = None
  game_type: Optional[str] = None

  @validator('interaction', always=True, pre=True)
  def validate_channel_id(cls, interaction):
    if interaction.channel.id != LOBBY_CHANNEL:
      handle_subcommand_error(interaction, DiscordErrorType.INVALID_CHANNEL)
    return interaction

  @validator('command', always=True, pre=True)
  def validate_command(cls, command, values):
    interaction = values.get('interaction')
    if command != 'lobby':
      handle_subcommand_error(interaction, DiscordErrorType.INVALID_COMMAND)
    return command

  @validator('subcommand_group', always=True, pre=True)
  def validate_subcommand_group(cls, subcommand_group, values):
    interaction = values.get('interaction')
    if subcommand_group not in ['create', 'set']:
      handle_subcommand_error(interaction, DiscordErrorType.INVALID_SUBCOMMAND_GROUP)
    return subcommand_group

  @validator('island_id', always=True, pre=True)
  def set_island_id(cls, island_id, values):
    subcommand_group = values.get('subcommand_group')
    subcommand = values.get('subcommand')
    if ((subcommand_group == 'set' and subcommand == 'island') or
      (subcommand_group == 'create' and subcommand != 'train')):
      island_id = values.get('param1')
    return island_id

  @validator('min_players', always=True, pre=True)
  def set_min_players(cls, min_players, values):
    subcommand_group = values.get('subcommand_group')
    subcommand = values.get('subcommand')
    if subcommand_group == 'create' and subcommand != 'train':
      min_players = values.get('param2')
    if subcommand_group == 'create' and subcommand == 'train':
      min_players = values.get('param1')
    return min_players

  @validator('username', always=True, pre=True)
  def set_username(cls, username, values):
    subcommand_group = values.get('subcommand_group')
    subcommand = values.get('subcommand')
    if subcommand_group == 'set' and subcommand == 'username':
      username = values.get('param1')
    return username

  @validator('game_type', always=True, pre=True)
  def set_game_type(cls, game_type, values):
    subcommand_group = values.get('subcommand_group')
    subcommand = values.get('subcommand')
    interaction = values.get('interaction')
    if subcommand_group == 'create':
      if subcommand in subcommand_game_type_map:
        game_type = subcommand_game_type_map[subcommand]
      else:
        handle_subcommand_error(interaction, DiscordErrorType.INVALID_SUBCOMMAND)
    if game_type and game_type not in GAME_TYPES:
      raise ValueError('Invalid game type')
    return game_type

def handle_subcommand(subcommand: Subcommand, player: Player):
  if subcommand.subcommand_group == 'create':
    island = None
    if subcommand.island_id:
      island = Island(id=subcommand.island_id)
      island.get_url()

    game = Game(
      game_type=subcommand.game_type,
      min_players=subcommand.min_players
    )

    eligibility = get_lobby_creation_eligibility(player=player, game=game, island=island)
    is_eligible = eligibility.get('eligibility', False)
    error_message = eligibility.get('error_message', 'Lobby creation not allowed')

    if not is_eligible:
      subcommand.interaction.ack_application_command(ephemeral=True)
      bot_followup_response(
        interaction=subcommand.interaction,
        ephemeral=True,
        json={'content': error_message}
      )
      abort(400, 'Lobby creation not allowed')

    subcommand.interaction.ack_application_command()

    lobby = Lobby(
      id=subcommand.interaction.message_id,
      channel_id=subcommand.interaction.channel.id,
      creation_time=now_iso_str(),
      creator=player,
      game=game,
      island=island,
      status='open',
      players=[player]
    )
    lobby.create()
    delayed_close_delete_lobby(
      channel_id=lobby.channel_id,
      lobby_id=lobby.id,
      delay_in_seconds=1200,
      only_if_open=True
    )
    bot_lobby_response(
      interaction=subcommand.interaction,
      lobby=lobby
    )

  if subcommand.subcommand_group == 'set' and subcommand.subcommand == 'username':
    subcommand.interaction.ack_application_command(ephemeral=True)
    player.set_username(subcommand.username)
    bot_followup_response(
      interaction=subcommand.interaction,
      ephemeral=True,
      json={'content': wrap_success_message('Username set')}
    )

  if subcommand.subcommand_group == 'set' and subcommand.subcommand == 'island':
    subcommand.interaction.ack_application_command(ephemeral=True)
    island = Island(id=subcommand.island_id)
    island.get_url()
    player.set_island(island)
    bot_followup_response(
      interaction=subcommand.interaction,
      ephemeral=True,
      json={'content': wrap_success_message('Island set')}
    )