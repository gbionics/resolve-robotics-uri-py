"""Usage: python custom_uri_override.py home://Documents/notes.txt"""

import argparse
from pathlib import Path

from resolve_robotics_uri_py import get_default_uri_overrides, resolve_robotics_uri


# Resolve home://Documents/notes.txt inside the current user's home directory.
def resolve_home(uri, **options):
    path = Path.home() / uri.partition(":")[2].removeprefix("//")
    return resolve_robotics_uri(str(path), uri_overrides={}, **options)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("uri")
    args = parser.parse_args()
    print(
        resolve_robotics_uri(
            args.uri,
            uri_overrides={**get_default_uri_overrides(), "home": resolve_home},
        )
    )


if __name__ == "__main__":
    main()
