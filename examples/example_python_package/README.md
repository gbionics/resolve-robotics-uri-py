# example_python_package

This example shows how a pure Python package can install a ROS-style resource into `share/` so
`resolve_robotics_uri_py` can find it with `package://example_python_package/cube.urdf`.

Install it from this directory with:

```bash
python -m pip install .
```

After installation, the URDF is available at:

```python
resolve_robotics_uri_py.resolve_robotics_uri("package://example_python_package/cube.urdf")
```

The installed file layout includes `share/example_python_package/cube.urdf`.

This is achieved by installing the `share` folder under the `<distribution>-<version>.data/data/` part of the wheel, that ends up being installed [directly in the python install prefix](https://packaging.python.org/en/latest/specifications/binary-distribution-format/).
