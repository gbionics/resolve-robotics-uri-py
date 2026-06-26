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

## Command Line usage

`resolve_robotics_uri_py` also install a command line tool called `resolve-robotics-uri-py` for use in scripts, that can be used as:

~~~bash
resolve-robotics-uri-py package://iCub/robots/iCubGazeboV2_7/model.urdf
~~~

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

You can find the detail how `resolve-robotics-uri-py`  find files in the [rru_spec.md](rru_spec.md) file.


## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html)
