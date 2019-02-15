"""Functions for generating visual displays of cards."""

import urllib


def image_html(card_name, width=146, height=204, highlighted=False):
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
    css_class = 'card-image'
    if highlighted:
        css_class += ' highlight'

    return '<img src="{}{}" width="{}" height="{}" class="{}" />'.format(url_prefix, params,
                                                                         width, height, css_class)


def cards_to_html(cards):
    """Returns HTML for scryfall images for a List[Card]. Images are all in one row."""
    return '\n'.join([image_html(card.name) for card in cards])


def card_names_to_html(card_names, highlighted=None):
    """Returns HTML for scryfall images for a list of card names. Images are all in one row."""
    return '\n'.join([image_html(name, highlighted=(name == highlighted)) for name in card_names])


def default_style():
    return """
    <style>
    card-image {
        display: inline;
        margin: 1px;
    }
    .highlight {
        border-width: 10px;
        border-color: red;
        border-style: solid;
    }
    .pack {
        border-color: black;   
        border-style: solid;
        padding: 5px;
    }
    </style>
"""
