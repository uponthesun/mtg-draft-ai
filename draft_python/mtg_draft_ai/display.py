import urllib


def image_html(card_name, width=146, height=204):
    url_prefix = 'https://api.scryfall.com/cards/named?'
    params = urllib.parse.urlencode({'format': 'image', 'exact': card_name})
    return '<img src="{}{}" width="{}" height="{}" class="card-image" />'.format(url_prefix,
                                                                                 params, width, height)


def cards_to_html(cards):
    return '\n'.join([image_html(card.name) for card in cards])


def card_names_to_html(card_names):
    return '\n'.join([image_html(name) for name in card_names])
