# `resolve_robotics_uri_py` File Search Rules

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

# URI overrides

Overrides are checked before normal URI/path processing. Keys are lowercase URI
scheme names without ":" or "//", e.g. `"home"`. The parsed scheme is matched
exactly, so `home://file` and `home:file` select the same handler; `homework://file`
does not. Override selection is case-insensitive. Windows drive paths bypass overrides.
The callback receives the full input URI and search options. Its result or failure
is final; no other handler or normal lookup is tried afterward. Empty or invalid
scheme names are rejected.

The `uri_overrides` keyword accepts a mapping of scheme names to callbacks with
signature `callback(uri, *, package_dirs, exclude_python_prefix, exclude_env_vars,
default_package_name) -> pathlib.Path`. Callbacks may raise exceptions. `None` uses
`get_default_uri_overrides()`, which returns a fresh mapping containing the
`robot://` callback. An explicit mapping
replaces the defaults; use `{}` to disable them, or unpack `get_default_uri_overrides()`
into a new mapping to extend them.

Callbacks can override built-in schemes as well as custom schemes. When delegating to
the resolver, remove the matching scheme override (or disable overrides) to avoid recursion.

# Robot-specific files via `robot://`

`robot://<relative-path>` resolves a robot-specific file. The optional default
package is supplied separately (`default_package_name`).
The URI authority and path together form the relative path, so
`robot://config/controller.ini` means `config/controller.ini`.

1. Return the regular file relative to the working directory, if present.
2. Select the robot from nonempty `ACTIVE_ROBOT_NAME`, falling back to nonempty
   `YARP_ROBOT_NAME`. Search `<root>/<package>/robots/<robot>/<relative-path>`
   under every immediate package directory in the normal search roots.
3. If a default package was supplied, search `<root>/<default-package>/<relative-path>`.
   Otherwise skip this step.

Only regular files match. Results are absolute canonical paths. Empty, absolute,
parent-traversing, or URI-valued relative paths are invalid. Nonempty robot and
package names must each be a single directory component. Multiple matches in the
winning tier return the first distinct canonical path in lexical order, with a warning.
Missing files raise `FileNotFoundError`; invalid inputs raise `ValueError`.

Discovery of package `robots` directories is cached by canonical search-root set
(up to 128 entries). File results and robot selection are not cached. After
installing new override packages, call `clear_robot_specific_file_cache()`
to refresh discovery.

# Command-line behaviour

The CLI passes its input to the URI resolver. Use `robot://config/controller.ini`
for robot lookup and `--default-package-name NAME` to add a default package. Plain paths
and other URI schemes retain normal resolution. Search path and exclusion flags
apply to robot lookup too.
