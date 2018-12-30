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

## Setup

1. cd into python project root
2. If using env manager, create a new environment, or activate your existing one
3. Run `pip install -e ".[test]"`
    * -e installs in "editable mode" - changes to your source files will automatically be used without needing to install again
    * [test] makes pip install the test dependencies as well

You can now run python scripts which use files from this project, e.g.:
```
python draft.py
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
```
pytest --cov=mtg_draft_ai
```