from pathlib import Path
from unittest.mock import patch

import pytest

from resolve_robotics_uri_py import get_default_uri_overrides, resolve_robotics_uri


def test_callbacks_receive_uri_and_options(tmp_path):
    seen = []

    def callback(uri, **options):
        seen.append((uri, options))
        return tmp_path / "result"

    options = dict(
        package_dirs=[str(tmp_path)],
        exclude_python_prefix=True,
        exclude_env_vars=["AMENT_PREFIX_PATH"],
        default_package_name="ControlLib",
    )
    for uri in (
        "custom://config.ini",
        "package://P/config.ini",
        "robot://config.ini",
        "file:///missing",
        "model://P/config.ini",
    ):
        assert (
            resolve_robotics_uri(
                uri, uri_overrides={uri.split(":")[0]: callback}, **options
            )
            == tmp_path / "result"
        )
        assert seen[-1] == (uri, options)


def test_exact_scheme_matching_and_no_implicit_fallback(tmp_path):
    def callback(uri, **options):
        return tmp_path / "result"

    overrides = {"custom": callback}
    for uri in ("custom://nested/file", "custom://file", "custom:resource", "CUSTOM://file"):
        assert resolve_robotics_uri(uri, uri_overrides=overrides) == tmp_path / "result"
    with pytest.raises(FileNotFoundError, match="non-supported scheme"):
        resolve_robotics_uri("customized://file", uri_overrides=overrides)

    def missing(uri, **options):
        raise FileNotFoundError("callback failed")

    local = tmp_path / "local.ini"
    local.touch()
    with pytest.raises(FileNotFoundError, match="callback failed"):
        resolve_robotics_uri(local.as_uri(), uri_overrides={"file": missing})
    for scheme in ("", "custom://", "custom://nested/", "custom:", "CUSTOM", "1custom"):
        with pytest.raises(ValueError, match="scheme names"):
            resolve_robotics_uri("anything", uri_overrides={scheme: callback})
    with pytest.raises(ValueError, match="callable"):
        resolve_robotics_uri("custom://file", uri_overrides={"custom": None})


def test_defaults_can_be_extended_replaced_or_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local = tmp_path / "local.ini"
    local.touch()
    overrides = {**get_default_uri_overrides(), "custom": lambda uri, **options: local}
    assert resolve_robotics_uri("robot://local.ini", uri_overrides=overrides) == local
    assert resolve_robotics_uri("custom://file", uri_overrides=overrides) == local
    with pytest.raises(FileNotFoundError):
        resolve_robotics_uri("robot://local.ini", uri_overrides={})
    # Explicit mappings do not alter the defaults of subsequent calls.
    assert resolve_robotics_uri("robot://local.ini") == local
    assert resolve_robotics_uri(str(local), uri_overrides={}) == local


def test_custom_handler_can_delegate(tmp_path):
    local = tmp_path / "file.ini"
    local.touch()

    def alias(uri, **options):
        return resolve_robotics_uri(local.as_uri(), uri_overrides={}, **options)

    assert resolve_robotics_uri("alias://file", uri_overrides={"alias": alias}) == local


def test_default_override_mappings_are_independent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local = tmp_path / "local.ini"
    local.touch()
    overrides = get_default_uri_overrides()
    overrides.clear()
    assert "robot" in get_default_uri_overrides()
    for uri in ("robot://local.ini", "robot:local.ini", "ROBOT://local.ini"):
        assert resolve_robotics_uri(uri) == local


@pytest.mark.parametrize(
    "uri",
    ["robot://local.ini", "custom://local.ini", "https://example.org/file", "https:resource"],
)
def test_unsupported_uri_is_rejected_before_path_resolution(uri):
    # Python 3.9 on Windows raises WinError 123 when resolving a URI as a path.
    with patch.object(Path, "resolve", side_effect=OSError(123, "Invalid path")):
        with pytest.raises(FileNotFoundError, match="non-supported scheme"):
            resolve_robotics_uri(uri, uri_overrides={})


@pytest.mark.parametrize("uri", [r"C:\folder\file.ini", "C:/folder/file.ini", "C:file.ini"])
def test_windows_drive_paths_do_not_dispatch_to_scheme_overrides(uri):
    def callback(uri, **options):
        raise AssertionError("A drive letter must not select a URI override")

    with patch.object(Path, "resolve", side_effect=FileNotFoundError("filesystem path")):
        with pytest.raises(FileNotFoundError, match="filesystem path"):
            resolve_robotics_uri(uri, uri_overrides={"c": callback})
