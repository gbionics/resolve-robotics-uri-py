import os
import pathlib
import subprocess
import sys

import pytest

from resolve_robotics_uri_py.resolve_robotics_uri_py import SupportedEnvVars


@pytest.mark.parametrize("legacy", [False, True])
def test_cli(tmp_path, legacy):
    root = tmp_path / "share"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    default = root / "ControlLib/config/controller.ini"
    override = root / "Overrides/robots/MyRobot/config/controller.ini"
    for path in (default, override):
        path.parent.mkdir(parents=True)
        path.touch()
    env = os.environ.copy()
    for name in SupportedEnvVars | {"ACTIVE_ROBOT_NAME", "YARP_ROBOT_NAME"}:
        env.pop(name, None)
    env["ACTIVE_ROBOT_NAME"] = "MyRobot"
    env["PYTHONPATH"] = str(pathlib.Path(__file__).resolve().parents[1] / "src")
    command = [
        sys.executable,
        "-m",
        "resolve_robotics_uri_py.resolve_robotics_uri_py",
        "--exclude-python-prefix",
        "--package_dirs",
        str(root),
    ]
    if legacy:
        command.append("--do-not-use-robot-specific-resolve")

    def run(*args):
        return subprocess.run(
            command + list(args), cwd=cwd, env=env, capture_output=True, text=True
        )

    result = run("config/controller.ini")
    assert result.returncode == (1 if legacy else 0)
    if not legacy:
        assert result.stdout.strip() == str(override)
    result = run("package://ControlLib/config/controller.ini")
    assert result.returncode == 0
    assert result.stdout.strip() == str(default)
    override.unlink()
    result = run("--package-name", "ControlLib", "config/controller.ini")
    assert result.returncode == (1 if legacy else 0)
    if not legacy:
        assert result.stdout.strip() == str(default)
    assert run("config/controller.ini").returncode == 1
    for path in (
        str(default),
        default.as_uri(),
        "model://ControlLib/config/controller.ini",
    ):
        result = run(path)
        assert result.returncode == 0
        assert result.stdout.strip() == str(default)
    local = cwd / "config/controller.ini"
    local.parent.mkdir()
    local.touch()
    result = run("config/controller.ini")
    assert result.returncode == 0
    assert result.stdout.strip() == str(local)
    result = run("missing.ini")
    assert result.returncode == 1
    assert result.stderr
    assert "Traceback" not in result.stderr
