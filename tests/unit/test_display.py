import os
import pytest
from mtg_draft_ai.display import *
from mtg_draft_ai.api import read_cube_toml
from .. import TEST_DATA_DIR


# Cards:
# Abzan Battle Priest, Ajani's Pridemate
@pytest.fixture
def cards():
    file_path = os.path.join(TEST_DATA_DIR, 'test_display_cards.toml')
    return read_cube_toml(file_path)


def test_image_html():
    html = image_html('Battle Hymn')

    assert html == '<img src="https://api.scryfall.com/cards/named?format=image&exact=Battle+Hymn" width="146" height="204" class="card-image" />'


def test_cards_to_html(cards):
    html = cards_to_html(cards)
    expected = """<img src="https://api.scryfall.com/cards/named?format=image&exact=Abzan+Battle+Priest" width="146" height="204" class="card-image" />
<img src="https://api.scryfall.com/cards/named?format=image&exact=Ajani%27s+Pridemate" width="146" height="204" class="card-image" />"""

    assert html == expected


def test_card_names_to_html():
    html = card_names_to_html(['Abzan Battle Priest', "Ajani's Pridemate"])
    expected = """<img src="https://api.scryfall.com/cards/named?format=image&exact=Abzan+Battle+Priest" width="146" height="204" class="card-image" />
<img src="https://api.scryfall.com/cards/named?format=image&exact=Ajani%27s+Pridemate" width="146" height="204" class="card-image" />"""

    assert html == expected
