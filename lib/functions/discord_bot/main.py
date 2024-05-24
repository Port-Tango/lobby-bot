import functions_framework
from flask import abort, jsonify
from discord import (
  validate_request,
  validate_application_command,
  bot_response,
  bot_error_response,
  bot_error_reply_response,
  Interaction,
  RequestType,
  ResponseType,
  DiscordErrorType
)
from database import (
  get_lobby,
  get_lobby_creation_eligibility,
  get_player_join_eligibility,
  delayed_close_delete_lobby,
  Lobby,
  Game,
  Island,
  Player
)
from messages import delete_message
from utils import wrap_error_message

subcommand_game_type_map = {
  'ctf': 'CTF',
  'spyhunt': 'Spyhunt',
  'zombies': 'Zombies',
  'dm_ffa': 'FFA DM'
}

@functions_framework.http
def handler(request):
  # pylint: disable=too-many-statements
  is_valid = validate_request(request)
  if not is_valid:
    abort(401, DiscordErrorType.INVALID_SIGNATURE.value)

  data = request.get_json(silent=True, cache=False)

  ## mandatory response to ping request
  if data['type'] == RequestType.PING.value:
    return jsonify({'type': ResponseType.PONG.value})

  interaction = Interaction(**data)

  player = None
  if 'member' in data:
    player = Player(
      id=data['member']['user']['id'],
      name=data['member']['user']['global_name']
    )

  if data['type'] == RequestType.APPLICATION_COMMAND.value:
    interaction.ack(response_type=ResponseType.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE.value)

    if player:
      validate_application_command(data=data, interaction=interaction)
      subcommand = data['data']['options'][0]['options'][0]['name']
      if subcommand not in subcommand_game_type_map:
        bot_error_response(
          interaction=interaction,
          error_message=wrap_error_message(DiscordErrorType.INVALID_SUBCOMMAND.value)
        )
        abort(400, DiscordErrorType.INVALID_SUBCOMMAND.value)

      island_id = data['data']['options'][0]['options'][0]['options'][0]['value']
      island = Island(id=island_id)
      island.get_url()

      min_players = data['data']['options'][0]['options'][0]['options'][1]['value']
      game = Game(
        game_type=subcommand_game_type_map[subcommand],
        min_players=min_players
      )

      lobby = Lobby(
        id=interaction.message_id,
        creator=player,
        game=game,
        island=island,
        players=[player],
        status='open'
      )

      eligibility = get_lobby_creation_eligibility(lobby=lobby)
      is_eligible = eligibility.get('eligibility', False)
      error_message = eligibility.get('error_message', 'Lobby creation not allowed')

      if not is_eligible:
        bot_error_response(interaction=interaction, error_message=error_message)
        abort(400, 'Lobby creation not allowed')

      lobby.create()
      delayed_close_delete_lobby(lobby_id=lobby.id, delay_in_seconds=1200, only_if_open=True)

  elif data['type'] == RequestType.MESSAGE_COMPONENT.value:
    interaction.ack(response_type=ResponseType.DEFERRED_UPDATE_MESSAGE.value)

    if player:
      custom_id = data['data']['custom_id']

      lobby = get_lobby(lobby_id=interaction.message_id)

      if custom_id == 'join_lobby' and lobby.status == 'open':
        eligibility = get_player_join_eligibility(player=player, lobby=lobby)
        is_eligible = eligibility.get('eligibility', False)
        error_message = eligibility.get('error_message', 'Lobby joining not allowed')

        if not is_eligible:
          bot_error_reply_response(interaction=interaction, error_message=error_message)
          abort(400, 'Lobby joining not allowed')

        lobby.add_player(player=player)

        if lobby.player_count >= lobby.game.min_players:
          lobby.close()
          delayed_close_delete_lobby(lobby_id=lobby.id, delay_in_seconds=600)

      elif custom_id == 'leave_lobby' and lobby.status == 'open':
        lobby.remove_player(player=player)

        if len(lobby.players) == 0:
          lobby.close()
          delete_message(message_id=lobby.id)
          return "OK", 200

  else:
    raise ValueError('Invalid request type')

  bot_response(interaction=interaction,lobby=lobby)

  return "OK", 200
