import requests
import toml


def _get_color_id(name):
    r = requests.get('https://api.scryfall.com/cards/named', params={'exact': name})
    card_json = r.json()
    return ''.join(card_json['color_identity'])


cards = toml.load('cube_81183_tag_data.toml')
#cards = toml.load('cube_6949_tag_data.toml')
fixers = [k for k, v in cards.items() if 'Fixer' in v['tags']]
fixers_with_color_ids = {name: _get_color_id(name) for name in fixers}

with open('cube_81183_fixer_data.toml', 'w') as f:
    toml.dump(fixers_with_color_ids, f)
