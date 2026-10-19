import argparse
import os
import pathlib
import sys
import sysconfig
import warnings
from functools import lru_cache
from typing import Callable, Iterable, Mapping, Union
from urllib.parse import urlparse
from urllib.request import url2pathname

# =====================
# URI resolving helpers
# =====================

# Supported URI schemes
SupportedSchemes = {"file", "package", "model"}

# Environment variables in the search path.
#
# * https://github.com/robotology/idyntree/issues/291
# * https://github.com/gazebosim/sdformat/issues/1234
#
# AMENT_PREFIX_PATH is the only "special" as we need to add
# "share" after each value, see https://github.com/stack-of-tasks/pinocchio/issues/1520
#
# This list specify the origin of each env variable:
#
# * AMENT_PREFIX_PATH:        Used in ROS2
# * GAZEBO_MODEL_PATH:        Used in Gazebo Classic
# * GZ_SIM_RESOURCE_PATH:     Used in Gazebo Sim >= 7
# * IGN_GAZEBO_RESOURCE_PATH: Used in Ignition Gazebo <= 7
# * ROS_PACKAGE_PATH:         Used in ROS1
# * SDF_PATH:                 Used in sdformat
#
SupportedEnvVars = {
    "AMENT_PREFIX_PATH",
    "GAZEBO_MODEL_PATH",
    "GZ_SIM_RESOURCE_PATH",
    "IGN_GAZEBO_RESOURCE_PATH",
    "ROS_PACKAGE_PATH",
    "SDF_PATH",
    "RRU_ADDITIONAL_PATHS",
}


# Function inspired from https://github.com/ami-iit/robot-log-visualizer/pull/51
def get_search_paths_from_envs(env_list: Iterable[str]) -> list[pathlib.Path]:
    # Read the searched paths from all the environment variables
    search_paths = [
        pathlib.Path(f.strip()) if (env != "AMENT_PREFIX_PATH") else pathlib.Path(f.strip()) / "share"
        for env in env_list
        if os.getenv(env) is not None
        for f in os.getenv(env).split(os.pathsep)
        if f.strip() != ""
    ]

    # Resolve and remove duplicate paths
    search_paths = list({path.resolve() for path in search_paths})

    # Keep only existing paths
    existing_search_paths = [path for path in search_paths if path.is_dir()]

    # Notify the user of non-existing paths
    if len(set(search_paths) - set(existing_search_paths)) > 0:
        msg = "resolve-robotics-uri-py: Ignoring non-existing paths from env vars: {}."
        warnings.warn(
            msg.format(
                pathlist_list_to_string(set(search_paths) - set(existing_search_paths))
            )
        )

    return existing_search_paths


def get_default_search_paths(
    exclude_python_prefix: bool = False,
    exclude_env_vars: Union[list[str], None] = None,
) -> list[pathlib.Path]:
    exclude_env_vars = set(exclude_env_vars or [])
    search_env_vars = SupportedEnvVars - exclude_env_vars
    search_paths = get_search_paths_from_envs(search_env_vars)

    if not exclude_python_prefix:
        search_prefixes = {pathlib.Path(sys.prefix).resolve()}
        sysconfig_data_prefix = sysconfig.get_path("data")

        if sysconfig_data_prefix:
            search_prefixes.add(pathlib.Path(sysconfig_data_prefix).resolve())

        # Avoid adding duplicate paths when sys.prefix and sysconfig.get_path("data")
        # map to the same location.
        seen_paths = {path.resolve() for path in search_paths}

        for prefix in search_prefixes:
            search_path_candidates = [prefix / "share"]

            # On Windows conda prefixes, data files are installed under
            # <prefix>/Library/share rather than <prefix>/share.
            if sys.platform == "win32":
                search_path_candidates.append(prefix / "Library" / "share")

            for candidate in search_path_candidates:
                if not candidate.is_dir():
                    continue

                resolved_candidate = candidate.resolve()

                if resolved_candidate in seen_paths:
                    continue

                seen_paths.add(resolved_candidate)
                search_paths.append(resolved_candidate)

    return search_paths


def pathlist_list_to_string(path_list: Iterable[Union[str, pathlib.Path]]) -> str:
    return " ".join(str(path) for path in path_list)


# ===================
# URI resolving logic
# ===================


def resolve_robotics_uri(
    uri: str,
    package_dirs: Union[list[str], None] = None,
    exclude_python_prefix: bool = False,
    exclude_env_vars: Union[list[str], None] = None,
    uri_overrides: Union[Mapping[str, Callable[..., pathlib.Path]], None] = None,
    default_package_name: str = "",
) -> pathlib.Path:
    """
    Resolve a robotics URI to an absolute filename.

    Args:
        uri: The URI to resolve.
        package_dirs: A list of additional paths to look for the file.
        exclude_python_prefix: If True, do not search Python installation prefixes.
        exclude_env_vars: Optional list of environment variable names to exclude from
            the default search path list.
        uri_overrides: URI scheme name to resolver callback mapping. None enables the
            default robot:// handler; an empty mapping disables overrides. The
            scheme is matched exactly, without ":" or "//" in the key. Callbacks
            receive the full URI and package_dirs, exclude_python_prefix,
            exclude_env_vars, default_package_name as keyword arguments. Their
            result or exception is returned directly.
        default_package_name: Optional default package for robot:// resolution,
            also available to other URI override callbacks.

    Returns:
        The absolute filename corresponding to the URI.

    Raises:
        FileNotFoundError: If no file corresponding to the URI is found.

    Note:
        By default the function will look for the file in the
        default search paths specified by the environment variables in `SupportedEnvVars`.

        If the `package_dirs` argument is provided, the model is also searched in the folders
        specified in `package_dirs` . In particular if a file is specified by the uri
        `package://ModelName/meshes/mesh.stl`, and the actual file is in
        `/usr/local/share/ModelName/meshes/mesh.stl`, the `package_dirs` should contain `/usr/local/share`.
    """
    parsed_uri = urlparse(uri)
    is_windows_drive_path = bool(pathlib.PureWindowsPath(uri).drive)
    overrides = get_default_uri_overrides() if uri_overrides is None else uri_overrides
    if any(
        not isinstance(scheme, str)
        or not scheme
        or urlparse(scheme + ":").scheme != scheme
        or not callable(callback)
        for scheme, callback in overrides.items()
    ):
        raise ValueError("URI overrides require lowercase scheme names and callable handlers")
    if not is_windows_drive_path and parsed_uri.scheme in overrides:
        return overrides[parsed_uri.scheme](
            uri,
            package_dirs=package_dirs,
            exclude_python_prefix=exclude_python_prefix,
            exclude_env_vars=exclude_env_vars,
            default_package_name=default_package_name,
        )
    package_dirs = package_dirs if isinstance(package_dirs, list) else [package_dirs]

    # Remove empty strings and None entries from the list
    package_dirs = list(
        {p for entry in package_dirs if entry for p in entry.split(os.pathsep) if p}
    )

    # If the URI has no scheme, use by default file:// which maps the resolved input
    # path to a URI with empty authority. Leave explicit URI schemes intact so
    # unsupported schemes are rejected before Windows filesystem normalization.
    if (
        parsed_uri.scheme
        and parsed_uri.scheme not in SupportedSchemes
        and not is_windows_drive_path
    ):
        msg = "resolve-robotics-uri-py: Passed URI '{}' use non-supported scheme '{}'"
        raise FileNotFoundError(msg.format(uri, parsed_uri.scheme))

    if not parsed_uri.scheme or is_windows_drive_path:
        uri = pathlib.Path(uri).resolve().as_uri()

    # Parse the URI to determine the scheme and path
    parsed_uri = urlparse(uri)

    # We only support the following URI schemes at the moment:
    #
    # * file:/      to pass an absolute file path directly
    # * model://    SDF-style model URI
    # * package://  ROS-style package URI
    #
    if parsed_uri.scheme not in SupportedSchemes:
        msg = "resolve-robotics-uri-py: Passed URI '{}' use non-supported scheme '{}'"
        raise FileNotFoundError(msg.format(uri, parsed_uri.scheme))

    # This is the file URI scheme as per RFC8089:
    # https://datatracker.ietf.org/doc/html/rfc8089

    if parsed_uri.scheme == "file":
        # Convert URI path to local filesystem path using url2pathname
        # This properly handles Windows paths like /C:/path/to/file -> C:\path\to\file
        local_path = url2pathname(parsed_uri.path)

        # Create the file path, resolving symlinks and '..'
        uri_file_path = pathlib.Path(local_path).resolve()

        # Check that the file exists
        if not uri_file_path.is_file():
            msg = "resolve-robotics-uri-py: No file corresponding to URI '{}' found"
            raise FileNotFoundError(msg.format(uri))

        return uri_file_path.resolve()

    # Strip the scheme from the URI
    uri_path = uri
    uri_path = uri_path.replace(f"{parsed_uri.scheme}://", "")

    # List of matching resources found
    model_filenames = []

    # Search the resource in the path from the env variables
    for folder in set(
        get_default_search_paths(exclude_python_prefix, exclude_env_vars)
    ) | {
        path
        for directory in package_dirs
        if directory and (path := pathlib.Path(directory).expanduser()).exists()
    }:
        # Join the folder from environment variable and the URI path
        candidate_file_name = folder / uri_path

        # Expand or resolve the file path (symlinks and ..)
        candidate_file_name = candidate_file_name.resolve()

        if not candidate_file_name.exists():
            continue

        # Skip if the file is already in the list
        if candidate_file_name not in model_filenames:
            model_filenames.append(candidate_file_name)

    if len(model_filenames) == 0:
        msg = "resolve-robotics-uri-py: No file corresponding to URI '{}' found"
        raise FileNotFoundError(msg.format(uri))

    if len(model_filenames) > 1:
        msg = "resolve-robotics-uri-py: "
        msg += "Multiple files ({}) found for URI '{}', returning the first one."
        warnings.warn(msg.format(pathlist_list_to_string(model_filenames), uri))

    if len(model_filenames) >= 1:
        assert model_filenames[0].exists()
        return pathlib.Path(model_filenames[0]).resolve()


@lru_cache(maxsize=128)
def _robot_directories(
    search_roots: tuple[pathlib.Path, ...],
) -> tuple[pathlib.Path, ...]:
    directories = set()
    for root in search_roots:
        try:
            for package in root.iterdir():
                robots = package / "robots"
                if package.is_dir() and robots.is_dir():
                    directories.add(robots.resolve())
        except OSError:
            # Missing or unreadable roots cannot provide an override.
            continue
    return tuple(sorted(directories))


def clear_robot_specific_file_cache() -> None:
    """Refresh discovery after installing new packages or robots directories."""
    _robot_directories.cache_clear()


def _resolve_robot_uri(
    uri: str,
    default_package_name: str = "",
    package_dirs: Union[list[str], None] = None,
    exclude_python_prefix: bool = False,
    exclude_env_vars: Union[list[str], None] = None,
) -> pathlib.Path:
    """Default robot:// callback: working directory, robot override, package default."""
    relative_path = uri.partition(":")[2].removeprefix("//")
    path = pathlib.Path(relative_path)
    if (
        not relative_path
        or path.is_absolute()
        or path.anchor
        or ".." in path.parts
        or urlparse(relative_path).scheme
    ):
        raise ValueError(
            "relative_path must be a nonempty relative filesystem path without '..' or a URI scheme"
        )

    def check_name(name: str, label: str) -> None:
        if not name or name in (".", "..") or any(c in name for c in "/\\:"):
            raise ValueError(f"{label} must be a single directory component")

    if default_package_name:
        check_name(default_package_name, "default_package_name")
    if path.is_file():
        return path.resolve()

    robot = os.getenv("ACTIVE_ROBOT_NAME") or os.getenv("YARP_ROBOT_NAME")
    if robot:
        check_name(robot, "robot name")
    entries = package_dirs if isinstance(package_dirs, list) else [package_dirs]
    roots = set(get_default_search_paths(exclude_python_prefix, exclude_env_vars))
    roots.update(
        pathlib.Path(directory).expanduser().resolve()
        for entry in entries
        if entry
        for directory in entry.split(os.pathsep)
        if directory
        if pathlib.Path(directory).expanduser().is_dir()
    )
    roots = tuple(sorted(roots))

    def find(candidates):
        matches = sorted(
            {candidate.resolve() for candidate in candidates if candidate.is_file()}
        )
        if len(matches) > 1:
            warnings.warn(
                "resolve-robotics-uri-py: Multiple files ({}) found for robot-specific "
                "file '{}', returning the first one.".format(
                    pathlist_list_to_string(matches), relative_path
                )
            )
        return matches[0] if matches else None

    if robot:
        result = find(
            directory / robot / path for directory in _robot_directories(roots)
        )
        if result is not None:
            return result
    if default_package_name:
        result = find(root / default_package_name / path for root in roots)
        if result is not None:
            return result
    raise FileNotFoundError(
        f"resolve-robotics-uri-py: No robot-specific or default file '{relative_path}' "
        f"found for package '{default_package_name}'"
    )


def get_default_uri_overrides() -> dict[str, Callable[..., pathlib.Path]]:
    """Return fresh default URI callbacks keyed by lowercase scheme names."""
    return {"robot": _resolve_robot_uri}


def main():
    parser = argparse.ArgumentParser(
        description="Utility resolve a robotics URI ({}) to an absolute filename.".format(
            ", ".join(f"{scheme}://" for scheme in SupportedSchemes | {"robot"})
        )
    )
    parser.add_argument(
        "uri", metavar="URI", type=str, help="URI or relative file path to resolve"
    )
    parser.add_argument(
        "--default-package-name",
        default="",
        metavar="NAME",
        help="Package providing a default for a robot:// URI",
    )
    parser.add_argument(
        "--package_dirs",
        metavar="PATH",
        type=str,
        help="Additional paths to look for the file",
        default=None,
    )
    parser.add_argument(
        "--exclude-python-prefix",
        action="store_true",
        help="Do not search Python installation prefixes",
    )
    parser.add_argument(
        "--exclude-env-var",
        action="append",
        default=[],
        metavar="NAME",
        help="Exclude an environment variable from the default search path list",
    )

    args = parser.parse_args()

    exclude_env_vars = set(args.exclude_env_var)

    try:
        search_options = dict(
            package_dirs=args.package_dirs,
            exclude_python_prefix=args.exclude_python_prefix,
            exclude_env_vars=list(exclude_env_vars),
        )
        result = resolve_robotics_uri(
            args.uri, default_package_name=args.default_package_name, **search_options
        )
    except (FileNotFoundError, ValueError) as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(result, file=sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
