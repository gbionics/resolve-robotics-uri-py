import pathlib
import tempfile

import resolve_robotics_uri_py


def _clear_supported_env_vars(monkeypatch):
    for env_var in resolve_robotics_uri_py.resolve_robotics_uri_py.SupportedEnvVars:
        monkeypatch.delenv(env_var, raising=False)


def test_default_search_paths_include_sysconfig_data_prefix(monkeypatch):
    _clear_supported_env_vars(monkeypatch)

    with tempfile.TemporaryDirectory() as sys_prefix_dir, tempfile.TemporaryDirectory() as data_prefix_dir:
        sys_prefix_path = pathlib.Path(sys_prefix_dir).resolve()
        data_prefix_path = pathlib.Path(data_prefix_dir).resolve()

        sys_prefix_share = sys_prefix_path / "share"
        data_prefix_share = data_prefix_path / "share"
        sys_prefix_share.mkdir(parents=True, exist_ok=True)
        data_prefix_share.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(resolve_robotics_uri_py.resolve_robotics_uri_py.sys, "prefix", str(sys_prefix_path))
        monkeypatch.setattr(
            resolve_robotics_uri_py.resolve_robotics_uri_py.sysconfig,
            "get_path",
            lambda name, *args, **kwargs: str(data_prefix_path) if name == "data" else None,
        )

        search_paths = resolve_robotics_uri_py.resolve_robotics_uri_py.get_default_search_paths()

        assert sys_prefix_share in search_paths
        assert data_prefix_share in search_paths


def test_default_search_paths_deduplicate_same_prefix(monkeypatch):
    _clear_supported_env_vars(monkeypatch)

    with tempfile.TemporaryDirectory() as common_prefix_dir:
        common_prefix_path = pathlib.Path(common_prefix_dir).resolve()
        common_share = common_prefix_path / "share"
        common_share.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(resolve_robotics_uri_py.resolve_robotics_uri_py.sys, "prefix", str(common_prefix_path))
        monkeypatch.setattr(
            resolve_robotics_uri_py.resolve_robotics_uri_py.sysconfig,
            "get_path",
            lambda name, *args, **kwargs: str(common_prefix_path) if name == "data" else None,
        )

        search_paths = resolve_robotics_uri_py.resolve_robotics_uri_py.get_default_search_paths()

        assert search_paths.count(common_share) == 1