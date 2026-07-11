# example_hatchling_package

This example shows the Hatchling-based layout used to ship a URDF from a pure Python package.

Install it from this directory with:

```bash
python -m pip install .
```

After installation, the URDF is available at:

```python
resolve_robotics_uri_py.resolve_robotics_uri("package://example_hatchling_package/cube.urdf")
```

The installed file layout includes `share/example_hatchling_package/cube.urdf`.

This is achieved by installing the `share` folder under the `<distribution>-<version>.data/data/` part of the wheel, that ends up being installed [directly in the python install prefix](https://packaging.python.org/en/latest/specifications/binary-distribution-format/).
