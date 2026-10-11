# `resolve_robotics_uri_py.resolve_robotics_uri` File Search Rules

`resolve_robotics_uri_py.resolve_robotics_uri` resolves URIs by following the rules below.

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

# Robot-specific files found by `resolve_robotics_uri_py.resolve_robot_specific_file`

`resolve_robotics_uri_py.resolve_robot_specific_file(relative_path, package_name="", ...)`
resolves a relative file path for a specific robot. The package name is optional.
It accepts the same search options as `resolve_robotics_uri`.

An input beginning with `package://` delegates directly to `resolve_robotics_uri`,
forwarding all search options. It ignores `package_name` and robot selection;
working-directory and robot overrides do not apply to that input.

Lookup of `resolve_robotics_uri_py.resolve_robot_specific_file` in three steps:

1. Return the file relative to the current working directory, if it is a regular file.
2. Select the robot from nonempty `ACTIVE_ROBOT_NAME`, falling back to nonempty
   `YARP_ROBOT_NAME`. Search `package://<package>/robots/<robot>/<relative-path>`
   for every immediate package directory in the normal search roots.
3. If a nonempty package name was specified, and either no override exists or no
   robot is selected, search `package://<default-package>/<relative-path>`.
   If the package name is omitted or empty, this step is skipped.

For relative paths, the result must be a regular file and is returned as an
absolute `pathlib.Path` with symlinks resolved. No match raises `FileNotFoundError`.
Invalid relative paths or nonempty package/robot names raise `ValueError`.
Multiple matches in the winning tier emit a warning and return the first distinct
canonical path in lexical order.

# Command-line behaviour

The CLI uses robot-specific resolution by default for relative paths and
`package://` inputs. The latter delegate to the original URI resolver as described
above. `file:` and `model:` URIs and absolute paths use the original URI resolver.
Use `--package-name NAME` to enable the package-default tier for relative paths;
without it, step 3 is skipped.

`--do-not-use-robot-specific-resolve` selects the original URI resolver for every
input, restoring the previous CLI behavior. In that mode, `--package-name` has no
effect. All existing search-path and exclusion options still apply in both modes.
