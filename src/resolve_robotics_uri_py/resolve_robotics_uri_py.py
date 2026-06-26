import argparse
import os
import pathlib
import sys
import sysconfig
import warnings
from typing import Union, Iterable
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
) -> pathlib.Path:
    """
    Resolve a robotics URI to an absolute filename.

    Args:
        uri: The URI to resolve.
        package_dirs: A list of additional paths to look for the file.
        exclude_python_prefix: If True, do not search Python installation prefixes.
        exclude_env_vars: Optional list of environment variable names to exclude from
            the default search path list.

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
    package_dirs = package_dirs if isinstance(package_dirs, list) else [package_dirs]

    # Remove empty strings and None entries from the list
    package_dirs = list(
        {p for entry in package_dirs if entry for p in entry.split(os.pathsep) if p}
    )

    # If the URI has no scheme, use by default file:// which maps the resolved input
    # path to a URI with empty authority
    if not any(uri.startswith(scheme) for scheme in SupportedSchemes):
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

        if not candidate_file_name.is_file():
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


def main():
    parser = argparse.ArgumentParser(
        description="Utility resolve a robotics URI ({}) to an absolute filename.".format(
            ", ".join(f"{scheme}://" for scheme in SupportedSchemes)
        )
    )
    parser.add_argument("uri", metavar="URI", type=str, help="URI to resolve")
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
        result = resolve_robotics_uri(
            args.uri,
            args.package_dirs,
            exclude_python_prefix=args.exclude_python_prefix,
            exclude_env_vars=list(exclude_env_vars),
        )
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    print(result, file=sys.stdout)
    sys.exit(0)


if __name__ == "__main__":
    main()
