import urllib
from multiprocessing.pool import ThreadPool

from mtg_draft_ai.api import read_cube_toml

import requests
import toml


class CubeData:

    def __init__(self, cards, image_urls):
        self.cards = cards
        self.image_urls = image_urls
        self.cards_by_name = {c.name: c for c in cards}

    @staticmethod
    def load(cube_file, image_urls_file, fixer_data_file):
        cards = read_cube_toml(cube_file, fixer_data_file)
        card_names = [c.name for c in cards]
        image_urls = _load_and_update_image_url_cache(card_names, image_urls_file)
        return CubeData(cards, image_urls)

    def card_by_name(self, card_name):
        return self.cards_by_name[card_name]

    def get_image_url(self, card_name):
        """ Gets the image URL for a card name from cache if present, otherwise falls back to the API URL. """
        if card_name in self.image_urls:
            return self.image_urls[card_name]

        # Fall back to using the API if we don't have the image URL cached (e.g. when viewing old drafts)
        query_string = urllib.parse.urlencode({'format': 'image', 'exact': card_name})
        return 'https://api.scryfall.com/cards/named?' + query_string


def _load_and_update_image_url_cache(card_names, image_urls_file):
    # Load cache from disk
    cache = toml.load(image_urls_file)

    # Filter out cards which are no longer in the cube list
    cache = {k: v for k, v in cache.items() if k in card_names}

    # Get URLs for new cards
    missing_cards = [name for name in card_names if name not in cache]
    with ThreadPool(10) as tp:
        urls = tp.map(_get_scryfall_image_url, missing_cards)

    for card_name, url in zip(missing_cards, urls):
        cache[card_name] = url

    # Write cache back out to disk
    with open(image_urls_file, 'w') as f:
        toml.dump(cache, f)

    return cache


def _get_scryfall_image_url(name):
    try:
        r = requests.get('https://api.scryfall.com/cards/named', params={'exact': name})
        card_json = r.json()
        if 'card_faces' in card_json and 'image_uris' in card_json['card_faces'][0]:
            # Case for double-faced cards
            # TODO: nice to have - show both sides of a DFC
            return card_json['card_faces'][0]['image_uris']['normal']
        return card_json['image_uris']['normal']
    except Exception as e:
        print('Failed to get image uri for card: {}'.format(card_json))
        raise e
