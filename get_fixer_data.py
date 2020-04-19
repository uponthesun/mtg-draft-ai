import sys
import requests
import toml


cube_list_file = sys.argv[1]

def _get_color_id(name):
    r = requests.get('https://api.scryfall.com/cards/named', params={'exact': name})
    card_json = r.json()
    return ''.join(card_json['color_identity'])


cards = toml.load(cube_list_file)
fixers = [k for k, v in cards.items() if 'Fixer' in v['tags']]
fixers_with_color_ids = {name: _get_color_id(name) for name in fixers}

print(toml.dumps(fixers_with_color_ids))
