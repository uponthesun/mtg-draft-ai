[Notes & Discussion](https://drive.google.com/drive/u/1/folders/1-En7mJJZp6nwMVRc2ImnGUVMvQ6Wkvo5)

# Developer Setup

## Prerequisites
* Python 3.4 or above
* Python environment manager (optional but recommended). One of:
  * virtualenv
  * conda
* Pip
  * Pip comes with virtualenv/conda. Otherwise, make sure it's installed on your system Python 3.

If you are not using virtualenv or conda, check to make sure your `python` 
and `pip` are both pointing to Python 3 before proceeding, by running:
```
python --version
pip --version
```

### Example virtualenv setup (run inside project root)
```
virtualenv --python=python3 venv
```
Creates a new virtual environment stored in a new directory called `venv` in the project root. `--python=python3` may not be necessary if you only have python3 installed on your system and not python2 as well.

```
source venv/bin/activate
```
Activates the virtual environment. You should always have the virtualenv active in your shell when running the tests or site.

## Setup

1. cd into python project root
2. If using env manager, create a new environment, or activate your existing one
3. Run `pip install -e ".[test]"`
    * -e installs in "editable mode" - changes to your source files will automatically be used without needing to install again
    * [test] makes pip install the test dependencies as well

You can now run python scripts which use files from this project, e.g.:
```
python trials.py 1
```

# Running Tests

Run all tests:
```
pytest
```

Run tests in specific file(s):
```
pytest tests/test_api.py
```

Run test with specific name:
```
pytest -k test_drafter_pick
```

Run tests and generate coverage report:

(Other options for --cov-report are available, e.g. html)
```
pytest --cov=mtg_draft_ai --cov-report term-missing
```

# Running the site locally

1-time setup:
```
cd website/draft_site
python manage.py migrate
```

Start the site:
```
python manage.py runserver
```

# Notebooks
Code used for trying out ideas for the AI / generating visualizations / etc. 

See [notebooks](notebooks)
