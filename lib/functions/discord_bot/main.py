import functions_framework
from flask import abort, jsonify
from discord import (
  validate_request,
  bot_lobby_response,
  bot_party_notification,
  bot_followup_response,
  Interaction,
  RequestType,
  DiscordErrorType,
)
from database import (
  get_player,
  get_lobby,
  get_player_join_eligibility,
  Player
)
from subcommand import handle_subcommand, Subcommand
from interactions import ResponseType

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

  if 'member' in data:
    player_id = data['member']['user']['id']
    player = get_player(player_id=player_id)
    if not player:
      player = Player(
        id=data['member']['user']['id'],
        name=data['member']['user']['global_name']
      )
      player.create()
    else:
      player.set_name(data['member']['user']['global_name'])

  if data['type'] == RequestType.APPLICATION_COMMAND.value:
    subcommand_group = data['data']['options'][0]

    subcommand_data = {
      'interaction': interaction,
      'command': data['data']['name'],
      'subcommand_group': subcommand_group['name'],
      'subcommand': subcommand_group['options'][0]['name'],
      'param1': subcommand_group['options'][0]['options'][0]['value']
    }

    if len(subcommand_group['options'][0]['options']) > 1:
      subcommand_data['param2'] = subcommand_group['options'][0]['options'][1]['value']

    subcommand = Subcommand(**subcommand_data)
    print(subcommand.dict())
    handle_subcommand(subcommand=subcommand, player=player)

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
          bot_followup_response(
            interaction=interaction,
            ephemeral=True,
            json={'content': error_message}
          )
          abort(400, 'Lobby joining not allowed')

        lobby.add_player(player=player)

        if lobby.player_count >= lobby.game.min_players:
          if lobby.game.game_type == 'Visit Train':
            lobby.randomize_players()
          lobby.close()
          bot_party_notification(lobby=lobby)
          return "OK", 200

      elif custom_id == 'leave_lobby' and lobby.status == 'open':
        lobby.remove_player(player=player)

        if len(lobby.players) == 0:
          lobby.close()
          return "OK", 200

      bot_lobby_response(interaction=interaction,lobby=lobby)

  else:
    raise ValueError('Invalid request type')

  return "OK", 200
