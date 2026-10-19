import pytest

from resolve_robotics_uri_py import DEFAULT_URI_OVERRIDE, resolve_robotics_uri


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
                uri, uri_override={uri.split(":")[0] + "://": callback}, **options
            )
            == tmp_path / "result"
        )
        assert seen[-1] == (uri, options)


def test_longest_prefix_and_no_implicit_fallback(tmp_path):
    def broad(uri, **options):
        return tmp_path / "broad"

    def specific(uri, **options):
        return tmp_path / "specific"

    overrides = {"custom://": broad, "custom://nested/": specific}
    assert (
        resolve_robotics_uri("custom://nested/file", uri_override=overrides)
        == tmp_path / "specific"
    )
    assert (
        resolve_robotics_uri("custom://file", uri_override=overrides)
        == tmp_path / "broad"
    )

    def missing(uri, **options):
        raise FileNotFoundError("callback failed")

    local = tmp_path / "local.ini"
    local.touch()
    with pytest.raises(FileNotFoundError, match="callback failed"):
        resolve_robotics_uri(local.as_uri(), uri_override={"file://": missing})
    with pytest.raises(ValueError, match="prefixes"):
        resolve_robotics_uri("anything", uri_override={"": broad})
    with pytest.raises(ValueError, match="callable"):
        resolve_robotics_uri("custom://file", uri_override={"custom://": None})


def test_defaults_can_be_extended_replaced_or_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    local = tmp_path / "local.ini"
    local.touch()
    overrides = {**DEFAULT_URI_OVERRIDE, "custom://": lambda uri, **options: local}
    assert resolve_robotics_uri("robot://local.ini", uri_override=overrides) == local
    assert resolve_robotics_uri("custom://file", uri_override=overrides) == local
    with pytest.raises(FileNotFoundError):
        resolve_robotics_uri("robot://local.ini", uri_override={})
    # Explicit mappings do not alter the defaults of subsequent calls.
    assert resolve_robotics_uri("robot://local.ini") == local
    assert resolve_robotics_uri(str(local), uri_override={}) == local


def test_custom_handler_can_delegate(tmp_path):
    local = tmp_path / "file.ini"
    local.touch()

    def alias(uri, **options):
        return resolve_robotics_uri(local.as_uri(), uri_override={}, **options)

    assert resolve_robotics_uri("alias://file", uri_override={"alias://": alias}) == local
