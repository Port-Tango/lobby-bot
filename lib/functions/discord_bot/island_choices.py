import random
import copy
import yaml

with open('islands.yaml', 'r', encoding='utf-8') as file:
  islands_config = yaml.safe_load(file)

def generate_island_choices(query, config=islands_config):
  # Make a deep copy of the configuration to avoid modifying the original
  config_copy = copy.deepcopy(config)

  # Extract and shuffle dev islands
  dev_islands = config_copy['dev']['islands']
  random.shuffle(dev_islands)

  # Extract and shuffle Port Tango islands
  port_tango_islands = config_copy['port_tango']['islands']
  random.shuffle(port_tango_islands)

  # Extract other integrators and shuffle their islands
  other_integrators = config_copy['integrators']
  for integrator in other_integrators:
    random.shuffle(integrator['islands'])

  # Randomize the order of the integrators themselves
  random.shuffle(other_integrators)

  # Initialize lists to hold the round-robin order
  round_robin_lists = (
    [dev_islands, port_tango_islands] +
    [integrator['islands'] for integrator in other_integrators]
  )

  # Perform round-robin selection until all lists are exhausted
  choices = []
  while any(round_robin_lists):
    for island_list in round_robin_lists:
      if island_list:  # Check if the current list is not exhausted
        island = island_list.pop(0)
        choices.append({'name': island['name'], 'value': island['id']})
  choices.insert(0, {"name": "🎲 Random from Party", "value": "random"})

  filtered_choices = [choice for choice in choices if query.lower() in choice['name'].lower()]
  return filtered_choices
