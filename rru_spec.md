# File Search Rules

`resolve_robotics_uri_py` resolves URIs by following the rules below.

## Supported URI Schemes

The resolver accepts these schemes:

- `file://`
- `package://`
- `model://`

If a path is passed without a scheme, it is treated as a local file path and converted to a `file://` URI.

## `file://` Resolution

For `file://` URIs, the path is converted to a local filesystem path and checked directly. The file must exist and be a regular file.

## `package://` and `model://` Resolution

For scoped URIs, the resolver strips the scheme and searches for the remaining relative path under a set of candidate directories.

The search order is:

1. Search paths derived from supported environment variables.
2. Search paths derived from Python installation prefixes, unless excluded.
3. Any directories passed explicitly through `package_dirs`.

If multiple matching files are found, the first one in the collected list is returned and a warning is emitted.

## Environment Variables Used For Search

The resolver reads these environment variables by default:

- `AMENT_PREFIX_PATH`
- `GAZEBO_MODEL_PATH`
- `GZ_SIM_RESOURCE_PATH`
- `IGN_GAZEBO_RESOURCE_PATH`
- `ROS_PACKAGE_PATH`
- `SDF_PATH`
- `RRU_ADDITIONAL_PATHS`

Each variable may contain multiple paths separated by `os.pathsep`.

Special handling applies to `AMENT_PREFIX_PATH`: each entry is interpreted as a prefix and `share` is appended before searching.

All other variables are searched as-is.

Non-existing entries are ignored, and a warning is emitted for them.

## Python Prefix Search Paths

By default, the resolver considers two Python installation prefixes:

- `sys.prefix`
- `sysconfig.get_path("data")`

For each prefix, it searches:

- `<prefix>/share`
- On Windows only: `<prefix>/Library/share`

This makes it possible to resolve ROS-style resources installed by pure Python packages that place files under `share/<package_name>/`.

You can disable Python-prefix-based search by passing `exclude_python_prefix=True` in Python or `--exclude-python-prefix` on the command line.

## Explicit Additional Directories

The `package_dirs` argument adds extra directories to the search set. Entries may be provided as a list or as a separator-delimited string.

These directories are searched in addition to the default environment-based paths and Python-prefix-based paths.

## Failure Behavior

If no matching file is found, the resolver raises `FileNotFoundError`.
