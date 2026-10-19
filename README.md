# resolve-robotics-uri-py

Pure Python package (that only depends on Python stdlib) to resolve a package:// (ROS-style) or model:// (Gazebo-style) URI to an absolute filename.

## Installation

Install using onle one of the following commands to install in an existing environment:

### Installation from conda-forge

```bash
conda install -c conda-forge resolve-robotics-uri-py
```

### Installation from PyPI

```bash
python -m pip install resolve-robotics-uri-py
```

## Usage in Python

Add `import resolve_robotics_uri_py` to your Python file, then take inspiration from the following examples.

If you want to get the location of the `iCubGazeboV2_7` iCub model installed from [`icub-models`](https://github.com/robotology/icub-models):

~~~python
absolute_path = resolve_robotics_uri_py.resolve_robotics_uri("package://iCub/robots/iCubGazeboV2_7/model.urdf")
~~~

If you want to get the location of the `ergoCubSN00`  model installed from [`ergocub-software`](https://github.com/icub-tech-iit/ergocub-software):

~~~python
absolute_path = resolve_robotics_uri_py.resolve_robotics_uri("package://ergoCub/robots/ergoCubSN000/model.urdf")
~~~

If you want to get the location of the `panda`  model installed by [`moveit_resources_panda_description`](https://index.ros.org/p/moveit_resources_panda_description/):

~~~python
absolute_path = resolve_robotics_uri_py.resolve_robotics_uri("package://moveit_resources_panda_description/urdf/panda.urdf")
~~~

## Robot-specific configuration files

Use `robot://` with the existing resolver:

```python
from resolve_robotics_uri_py import resolve_robotics_uri

absolute_path = resolve_robotics_uri(
    "robot://config/controller.ini", default_package_name="ControlLib"
)
```

For example, install the default at `share/ControlLib/config/controller.ini` and
an override at `share/CompanyRobotConfigurations/robots/MyRobot/config/controller.ini`.
Set `ACTIVE_ROBOT_NAME=MyRobot` (or `YARP_ROBOT_NAME` as a fallback). The lookup is:

1. A regular file at `config/controller.ini` in the working directory.
2. The robot-specific file under any immediate package's `robots/<robot>` directory.
3. The default package file, if a default package name was supplied.

Results are absolute paths to regular files. Discovery of `robots` directories is
cached; see [the search specification](rru_spec.md) for refresh and error behavior.

### Custom URI overrides

`uri_overrides` maps URI scheme names to callbacks. Keys omit `://`, e.g. `"home"`,
and match the parsed scheme exactly before normal resolution. The callback
receives the full URI and the search options as keyword arguments and returns a `pathlib.Path` or raises an exception.
A callback's failure does not fall back to another handler.

```python
from pathlib import Path
from resolve_robotics_uri_py import get_default_uri_overrides, resolve_robotics_uri

# Resolve home://Documents/notes.txt inside the current user's home directory.
def resolve_home(uri, **options):
    path = Path.home() / uri.partition(":")[2].removeprefix("//")
    return resolve_robotics_uri(str(path), uri_overrides={}, **options)


absolute_path = resolve_robotics_uri(
    "home://Documents/notes.txt",
    uri_overrides={**get_default_uri_overrides(), "home": resolve_home},
)
```

`get_default_uri_overrides()` returns a fresh mapping that callers can modify
without affecting subsequent resolutions.

This resolves `home://Documents/notes.txt` to `Documents/notes.txt` under the user's
home directory, while retaining `robot://`. The callback also receives
`default_package_name`, so custom overrides can use it for their own fallback logic.
A runnable version is in [examples/custom_uri_override.py](examples/custom_uri_override.py).

Omitting `uri_overrides` uses the default `robot://` handler. An explicit mapping
replaces the defaults; `uri_overrides={}` disables all overrides. Existing schemes
can be replaced too, e.g. a `"model"` callback could resolve models from an
application-specific directory. Callbacks that call the resolver again should
remove their own scheme or use an empty mapping to avoid recursion.

## Command Line usage

`resolve_robotics_uri_py` also install a command line tool called `resolve-robotics-uri-py` for use in scripts, that can be used as:

~~~bash
resolve-robotics-uri-py package://iCub/robots/iCubGazeboV2_7/model.urdf
~~~

Use an explicit `robot://` URI for robot-specific lookup:

```bash
resolve-robotics-uri-py robot://config/controller.ini
resolve-robotics-uri-py --default-package-name ControlLib robot://config/controller.ini
```

The default package name is optional; without it, the package-default lookup is skipped.

For example,  on bash this can be used to easily convert the a urdf specified via `package://` to an sdf (assuming you have Gazebo installed), using the [backtick operator](https://www.redhat.com/sysadmin/backtick-operator-vs-parens):
~~~bash
gz sdf -p `resolve-robotics-uri-py package://iCub/robots/iCubGazeboV2_7/model.urdf`
~~~

### Adding Custom Search Paths

Some packages may not be installed in standard locations, or you may want to use a custom directory structure. In such cases, you have a few options:

#### Option 1: Modify the Native Search Paths

You can add the search path to one of the natively supported paths of Gazebo or ROS, such as:

* `GZ_SIM_RESOURCE_PATH`
* `AMENT_PREFIX_PATH`

#### Option 2: Specify Additional Search Paths

If you prefer not to modify the default ROS or Gazebo search paths, you can use either the `--package_dirs` command line option or set the `RRU_ADDITIONAL_PATHS` environment variable:

##### Using the `--package_dirs` Command Line Option:

~~~bash
resolve-robotics-uri-py --package_dirs /path/to/packages:/another/path package://my_package/model.urdf
~~~

##### Setting the `RRU_ADDITIONAL_PATHS` Environment Variable:

~~~bash
export RRU_ADDITIONAL_PATHS=/path/to/packages:/another/path
resolve-robotics-uri-py package://my_package/model.urdf
~~~

Both methods accept a colon-separated list of directories (or semicolon-separated on Windows).

In Python code, you can specify additional paths using the `additional_package_dirs` parameter:

~~~python
absolute_path = resolve_robotics_uri_py.resolve_robotics_uri(
     "package://my_package/model.urdf",
     package_dirs=["/path/to/packages", "/another/path"]
)
~~~

## Details on how files are searched

You can find the details on how `resolve-robotics-uri-py` find files in the [rru_spec.md](rru_spec.md) file.


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html)
