import os
import pathlib
import subprocess
import sys
import warnings

import pytest

from resolve_robotics_uri_py import resolve_robotics_uri
from resolve_robotics_uri_py import resolve_robotics_uri_py as resolver


@pytest.mark.parametrize("scheme", ["package", "model"])
def test_search_precedence(tmp_path, monkeypatch, scheme):
    for name in resolver.SupportedEnvVars:
        monkeypatch.delenv(name, raising=False)
    roots = [tmp_path / str(i) for i in range(11)]
    roots[0] = tmp_path / "ament/share"
    roots[8] = tmp_path / "prefix/share"
    roots[9] = tmp_path / "data-prefix/share"
    files = []
    for root in roots:
        resource = root / "mypkg/model.urdf"
        resource.parent.mkdir(parents=True)
        resource.touch()
        files.append(resource)

    # Environment-variable order, entries within one variable, two Python prefixes,
    # and caller-supplied roots all take precedence over the following entries.
    monkeypatch.setenv("AMENT_PREFIX_PATH", str(roots[0].parent))
    monkeypatch.setenv(
        "GAZEBO_MODEL_PATH",
        os.pathsep.join(str(p) for p in (roots[1], roots[2], roots[1])),
    )
    for name, root in zip(
        (
            "GZ_SIM_RESOURCE_PATH",
            "IGN_GAZEBO_RESOURCE_PATH",
            "ROS_PACKAGE_PATH",
            "SDF_PATH",
            "RRU_ADDITIONAL_PATHS",
        ),
        roots[3:8],
    ):
        monkeypatch.setenv(name, str(root))
    monkeypatch.setattr(resolver.sys, "prefix", str(roots[8].parent))
    monkeypatch.setattr(
        resolver.sysconfig, "get_path", lambda name: str(roots[9].parent)
    )
    assert resolver.get_default_search_paths() == roots[:10]
    kwargs = {"package_dirs": [str(roots[10]), str(roots[1]), str(roots[10])]}
    uri = f"{scheme}://mypkg/model.urdf"
    for expected in files[:-1]:
        with pytest.warns(UserWarning, match="Multiple files"):
            assert resolve_robotics_uri(uri, **kwargs) == expected
        expected.unlink()
    assert resolve_robotics_uri(uri, **kwargs) == files[-1]


@pytest.mark.parametrize("scheme", ["package", "model"])
@pytest.mark.parametrize("as_list", [True, False])
def test_package_dirs_order_across_hash_seeds(tmp_path, monkeypatch, scheme, as_list):
    for name in resolver.SupportedEnvVars:
        monkeypatch.delenv(name, raising=False)
    roots = [tmp_path / "first", tmp_path / "second"]
    for root in roots:
        resource = root / "mypkg/model.urdf"
        resource.parent.mkdir(parents=True)
        resource.touch()
    entries = [str(roots[0]), str(roots[1]), str(roots[0])]
    package_dirs = entries if as_list else os.pathsep.join(entries)
    script = (
        "from resolve_robotics_uri_py import resolve_robotics_uri; "
        f"print(resolve_robotics_uri('{scheme}://mypkg/model.urdf', "
        f"package_dirs={package_dirs!r}, exclude_python_prefix=True))"
    )
    for seed in ("0", "1", "2", "3"):
        env = os.environ.copy()
        env["PYTHONHASHSEED"] = seed
        env["PYTHONPATH"] = str(pathlib.Path(resolver.__file__).resolve().parents[1])
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout.strip() == str(roots[0] / "mypkg/model.urdf")
        assert "Multiple files" in result.stderr


@pytest.mark.parametrize("scheme", ["package", "model"])
def test_duplicate_roots_do_not_warn(tmp_path, monkeypatch, scheme):
    for name in resolver.SupportedEnvVars:
        monkeypatch.delenv(name, raising=False)
    resource = tmp_path / "mypkg/model.urdf"
    resource.parent.mkdir()
    resource.touch()
    monkeypatch.setenv("GAZEBO_MODEL_PATH", os.pathsep.join([str(tmp_path)] * 2))
    monkeypatch.setenv("RRU_ADDITIONAL_PATHS", str(tmp_path / "."))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert (
            resolve_robotics_uri(
                f"{scheme}://mypkg/model.urdf",
                package_dirs=[str(tmp_path), str(tmp_path)],
                exclude_python_prefix=True,
            )
            == resource
        )
