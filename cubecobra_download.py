import csv
import sys
import time
import toml
import requests

cube_id = sys.argv[1]
data_file_name = sys.argv[2]

with open(data_file_name, 'r') as f:
    CURRENT_DATA = toml.load(f)

url = 'https://cubecobra.com/cube/download/csv/{}?primary=Color%20Category&secondary=Types-Multicolor&tertiary=CMC2'
response = requests.get(url.format(cube_id))
lines = [row for row in response.content.decode('utf-8').split('\r\n') if len(row) > 0]
reader = csv.reader(lines)
csv_rows = [row for row in reader]

keys = csv_rows[0]
card_rows = csv_rows[1:]
cards_from_csv = [{k: v for k, v in zip(keys, row)} for row in card_rows]
cards_by_name = {card['Name']: card for card in cards_from_csv}

def type_line_to_types(type_line):
    types = type_line.split('-')[0].strip().split(' ')
    return [t.lower() for t in types if t != 'Legendary']


def get_mana_cost(name):
    if name in CURRENT_DATA and 'mana_cost' in CURRENT_DATA[name]:
        return CURRENT_DATA[name]['mana_cost']

    mana_cost_scryfall = get_mana_cost_scryfall(name)
    result = list(mana_cost_scryfall.replace('{', '').replace('}', ''))
    print('Mana cost from scryfall for {}: {}'.format(name, result))
    return result


def get_mana_cost_scryfall(name):
    try:
        r = requests.get('https://api.scryfall.com/cards/named', params={'exact': name})
        card_json = r.json()
        if 'card_faces' in card_json and 'mana_cost' in card_json['card_faces'][0]:
            # Case for double-faced cards
            return card_json['card_faces'][0]['mana_cost']
        return card_json['mana_cost']
    except Exception as e:
        print('Failed to get mana cost for card: {}'.format(card_json))
        raise e
    finally:
        time.sleep(0.2)


def convert_cubecobra_card(name, card):
    return {
        'mana_cost': get_mana_cost(name),
        'color_identity': card['Color'],
        'types': type_line_to_types(card['Type']),
        'tags': [t.strip() for t in card['Tags'].split(',')]
    }


converted_cards_by_name = {name: convert_cubecobra_card(name, card) for name, card in cards_by_name.items()}

with open(data_file_name, 'w') as f:
    toml.dump(converted_cards_by_name, f)
