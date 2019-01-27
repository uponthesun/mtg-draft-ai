"""Functions for generating visual displays of cards."""

import urllib


def image_html(card_name, width=146, height=204):
    """Formats an img tag for the scryfall card image.

    Args:
        card_name (str): Card name.
        width (int): Optional - width in pixels.
        height (int): Optional - height in pixels.

    Returns:
        The HTML for the img tag for the scryfall card image.
    """
    url_prefix = 'https://api.scryfall.com/cards/named?'
    params = urllib.parse.urlencode({'format': 'image', 'exact': card_name})
    return '<img src="{}{}" width="{}" height="{}" class="card-image" />'.format(url_prefix,
                                                                                 params, width, height)


def cards_to_html(cards):
    """Returns HTML for scryfall images for a List[Card]. Images are all in one row."""
    return '\n'.join([image_html(card.name) for card in cards])


def card_names_to_html(card_names):
    """Returns HTML for scryfall images for a list of card names. Images are all in one row."""
    return '\n'.join([image_html(name) for name in card_names])
