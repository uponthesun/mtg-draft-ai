import json
import urllib.request
from bs4 import BeautifulSoup
from ratelimiter import RateLimiter
from retrying import retry

CUBE_TUTOR_URL = 'http://www.cubetutor.com/viewcube/{}'
CARD_HTML_CLASS = 'cardPreview'

@retry(stop_max_attempt_number=3)
@RateLimiter(max_calls=100, period=1)
def download_cube(cube_id):
    """Downloads the cube data for the given cube id and parses out the cards in the cube.
    This is rate limited to avoid completely overwhelming the service, and retries on failures.

    Args:
        cube_id (int): The id of the cube to retrieve cards for.
    Returns:
        list of String: The list of cards contained in the cube with the given id.
    """
    cube_url = CUBE_TUTOR_URL.format(cube_id)
    with urllib.request.urlopen(cube_url) as response:
        cube_page = response.read()
        soup = BeautifulSoup(cube_page, 'html.parser')
        card_elements = soup.find_all('a', class_=CARD_HTML_CLASS)
        card_names = [e.text for e in card_elements]
        return card_names
    return []

def write_cube_file(file_prefix, index, cube_data):
    """Writes the given list of cubes to a file, with one cube per line.

    Args:
        file_prefix (String): The prefix to use for writing the file.
        index (int): The suffix index to use for generating a unique file name.
        cube_data (list of list of String): The list of cubes containing their card data.
    """
    filename = file_prefix + '{}.txt'.format(index)
    with open(filename, 'w') as file:
        file.write('\n'.join([json.dumps(cube) for cube in cube_data]))

def download_cubes(file_prefix, file_size=100, min_id=1, max_id=100000):
    """Downloads the cube data for all cubes with id in the provided range.

    Args:
        file_prefix (String): The prefix to use for writing the cubes to files.
        file_size (String): The number of cubes to write per file.
        min_id (int): The id of the first cube to retrieve.
        max_id (int): The id of the last cube to retrieve.
    """
    cubes = []
    for i in range(min_id, max_id+1):
        print('Downloading cube {}...'.format(i))
        cubes.append(download_cube(i))
        if i % file_size == 0:
            write_cube_file(file_prefix, i//file_size, cubes)
            cubes = []
    if len(cubes) > 0:
        write_cube_file(file_prefix, i//file_size + 1, cubes)