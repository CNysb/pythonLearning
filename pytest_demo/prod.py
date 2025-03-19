from typing import List, Dict
from pathlib import Path
import os


BASE_LOCATION: Path = None
TEST_LOCATION: Path = None
DEMO_LIST: List = list()


def set_location():
    global BASE_LOCATION
    global TEST_LOCATION
    BASE_LOCATION = Path(__file__).parent.parent
    TEST_LOCATION = Path(__file__).parent


def get_dir():
    global DEMO_LIST
    for x in Path(os.path.join(BASE_LOCATION, "demo")).iterdir():
        print(str(x))
        if x.name.endswith(".idea") or x.name.endswith("cache"):
            continue
        if x.is_dir():
            DEMO_LIST.append(x)


def show():
    list(map(lambda x: print(x.name), DEMO_LIST))


def execute():
    set_location()
    get_dir()
    show()


if __name__ == "__main__":
    execute()
