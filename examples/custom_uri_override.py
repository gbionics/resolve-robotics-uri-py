"""Usage: python custom_uri_override.py CONFIG_ROOT config://controller.ini"""

import argparse
from pathlib import Path

from resolve_robotics_uri_py import DEFAULT_URI_OVERRIDE, resolve_robotics_uri


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config_root", type=Path)
    parser.add_argument("uri")
    args = parser.parse_args()

    # Resolve config:// URIs relative to an application-specific directory.
    def resolve_config(uri, **options):
        path = args.config_root.resolve() / uri[len("config://") :]
        return resolve_robotics_uri(str(path), uri_override={}, **options)

    print(
        resolve_robotics_uri(
            args.uri,
            uri_override={**DEFAULT_URI_OVERRIDE, "config://": resolve_config},
        )
    )


if __name__ == "__main__":
    main()
