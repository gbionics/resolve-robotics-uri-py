import pytest

from resolve_robotics_uri_py import (
    clear_robot_specific_file_cache,
    resolve_robotics_uri,
)
from resolve_robotics_uri_py.resolve_robotics_uri_py import (
    SupportedEnvVars,
    _robot_directories,
)


def resolve_robot_uri(path, default_package_name="", **options):
    uri = path if path.startswith("package://") else "robot://" + path
    return resolve_robotics_uri(uri, default_package_name=default_package_name, **options)


@pytest.fixture
def layout(tmp_path, monkeypatch):
    for name in SupportedEnvVars | {"ACTIVE_ROBOT_NAME", "YARP_ROBOT_NAME"}:
        monkeypatch.delenv(name, raising=False)
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    clear_robot_specific_file_cache()
    yield tmp_path / "share", cwd
    clear_robot_specific_file_cache()


def write(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path.resolve()


def resolve(root, **kwargs):
    return resolve_robot_uri(
        "config/controller.ini",
        "ControlLib",
        package_dirs=[str(root)],
        exclude_python_prefix=True,
        **kwargs
    )


def test_precedence_and_robot_selection(layout, monkeypatch):
    root, cwd = layout
    default = write(root / "ControlLib/config/controller.ini")
    active = write(root / "CompanyConfigurations/robots/MyRobot/config/controller.ini")
    yarp = write(root / "OtherPackage/robots/YarpRobot/config/controller.ini")
    assert resolve(root) == default
    monkeypatch.setenv("YARP_ROBOT_NAME", "YarpRobot")
    assert resolve(root) == yarp
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    assert resolve(root) == active
    local = write(cwd / "config/controller.ini")
    assert resolve(root) == local
    local.unlink()
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MissingRobot")
    assert resolve(root) == default  # Do not try YARP's robot when ACTIVE is set.
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "")
    assert resolve(root) == yarp
    yarp.unlink()
    assert resolve(root) == default
    default.unlink()
    with pytest.raises(FileNotFoundError):
        resolve(root)


def test_files_only_and_single_package_component(layout, monkeypatch):
    root, cwd = layout
    default = write(root / "ControlLib/config/controller.ini")
    (cwd / "config/controller.ini").mkdir(parents=True)
    (root / "Override/robots/MyRobot/config/controller.ini").mkdir(parents=True)
    write(root / "Nested/package/robots/MyRobot/config/controller.ini")
    write(root / "robots/MyRobot/config/controller.ini")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    assert resolve(root) == default
    default.unlink()
    default.mkdir()
    with pytest.raises(FileNotFoundError):
        resolve(root)


def test_discovery_cache_and_file_changes(layout, monkeypatch):
    root, _ = layout
    default = write(root / "ControlLib/config/controller.ini")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    assert resolve(root) == default
    misses = _robot_directories.cache_info().misses
    override = write(root / "NewPackage/robots/MyRobot/config/controller.ini")
    assert resolve(root) == default
    assert _robot_directories.cache_info().misses == misses
    clear_robot_specific_file_cache()
    assert resolve(root) == override
    override.unlink()
    assert resolve(root) == default
    override.touch()
    assert resolve(root) == override  # File results themselves are not cached.
    other_root = root.parent / "other_share"
    other = write(other_root / "Package/robots/MyRobot/config/controller.ini")
    assert resolve(other_root) == other


def test_search_options_and_ambiguity(layout, monkeypatch):
    root, _ = layout
    default = write(root / "ControlLib/config/controller.ini")
    first = write(root / "A/robots/MyRobot/config/controller.ini")
    write(root / "Z/robots/MyRobot/config/controller.ini")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    monkeypatch.setenv("AMENT_PREFIX_PATH", str(root.parent))
    with pytest.warns(UserWarning, match="Multiple files"):
        assert (
            resolve_robot_uri(
                "config/controller.ini", "ControlLib", exclude_python_prefix=True
            )
            == first
        )
    with pytest.raises(FileNotFoundError):
        resolve_robot_uri(
            "config/controller.ini",
            "ControlLib",
            exclude_python_prefix=True,
            exclude_env_vars=["AMENT_PREFIX_PATH"],
        )
    monkeypatch.delenv("ACTIVE_ROBOT_NAME")
    assert resolve(root) == default
    monkeypatch.setattr("sys.prefix", str(root.parent))
    assert (
        resolve_robot_uri(
            "config/controller.ini",
            "ControlLib",
            exclude_env_vars=["AMENT_PREFIX_PATH"],
        )
        == default
    )


@pytest.mark.parametrize(
    "path,package",
    [
        ("", "ControlLib"),
        ("/absolute", "ControlLib"),
        ("../outside", "ControlLib"),
        ("file:/absolute", "ControlLib"),
        ("file", "a/b"),
        ("file", ".."),
    ],
)
def test_invalid_input(layout, path, package):
    with pytest.raises(ValueError):
        resolve_robot_uri(path, package, exclude_python_prefix=True)


def test_invalid_robot(layout, monkeypatch):
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "../outside")
    with pytest.raises(ValueError):
        resolve(layout[0])


def test_override_in_other_search_root(layout, monkeypatch):
    root, _ = layout
    default = write(root / "ControlLib/config/controller.ini")
    other_root = root.parent / "other_share"
    override = write(other_root / "Package/robots/MyRobot/config/controller.ini")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    monkeypatch.setenv("RRU_ADDITIONAL_PATHS", str(other_root))
    assert resolve(root) == override
    assert resolve(root, exclude_env_vars=["RRU_ADDITIONAL_PATHS"]) == default


def test_symlinked_package_and_deduplicated_roots(layout, monkeypatch):
    root, _ = layout
    root.mkdir()
    external = root.parent / "external_package"
    override = write(external / "robots/MyRobot/config/controller.ini")
    try:
        (root / "Link").symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    assert (
        resolve_robot_uri(
            "config/controller.ini",
            "ControlLib",
            package_dirs=[str(root), str(root / ".")],
            exclude_python_prefix=True,
        )
        == override
    )


def test_package_uri_delegates(layout, monkeypatch):
    root, cwd = layout
    default = write(root / "ControlLib/config/controller.ini")
    write(root / "Overrides/robots/MyRobot/config/controller.ini")
    write(cwd / "config/controller.ini")
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    uri = "package://ControlLib/config/controller.ini"
    assert (
        resolve_robot_uri(
            uri, package_dirs=[str(root)], exclude_python_prefix=True
        )
        == default
    )
    # Neither an unrelated package name nor invalid robot selection affects URIs.
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "../invalid")
    assert (
        resolve_robot_uri(
            uri, "other/package", package_dirs=[str(root)], exclude_python_prefix=True
        )
        == default
    )
    monkeypatch.setenv("RRU_ADDITIONAL_PATHS", str(root))
    assert resolve_robot_uri(uri, exclude_python_prefix=True) == default
    with pytest.raises(FileNotFoundError):
        resolve_robot_uri(
            uri, exclude_python_prefix=True, exclude_env_vars=["RRU_ADDITIONAL_PATHS"]
        )
    default.unlink()
    with pytest.raises(FileNotFoundError):
        resolve_robot_uri(
            uri, package_dirs=[str(root)], exclude_python_prefix=True
        )


def test_no_package_skips_default(layout, monkeypatch):
    root, cwd = layout
    write(root / "config/controller.ini")
    write(root / "ControlLib/config/controller.ini")
    options = dict(package_dirs=[str(root)], exclude_python_prefix=True)
    for package in ((), ("",)):
        with pytest.raises(FileNotFoundError):
            resolve_robot_uri("config/controller.ini", *package, **options)
    monkeypatch.setenv("ACTIVE_ROBOT_NAME", "MyRobot")
    override = write(root / "Overrides/robots/MyRobot/config/controller.ini")
    clear_robot_specific_file_cache()
    assert resolve_robot_uri("config/controller.ini", **options) == override
    local = write(cwd / "config/controller.ini")
    assert resolve_robot_uri("config/controller.ini", **options) == local
