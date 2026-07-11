from __future__ import annotations

from pathlib import Path

from setuptools import setup

_SHARE_DIR = Path("share")


def _ensure_ament_resource_marker() -> Path:
    marker = Path("build") / "ament_resource_marker" / "example_setuptools_package"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch(exist_ok=True)
    return marker


def _build_data_files() -> list[tuple[str, list[str]]]:
    """Recursively collect share/ into wheel data-files without manual enumeration."""
    install_share = Path("share")
    package_share = install_share / "example_setuptools_package"
    data_files: dict[str, list[str]] = {}
    if _SHARE_DIR.is_dir():
        for path in sorted(_SHARE_DIR.rglob("*")):
            if not path.is_file():
                continue
            rel_dir = path.parent.relative_to(_SHARE_DIR)
            target = str(install_share / rel_dir)
            data_files.setdefault(target, []).append(str(path))

    # Install package metadata where ROS tools expect it, but keep it in
    # the root of the package so colcon can find it when building from source
    package_xml = Path("package.xml")
    if package_xml.is_file():
        data_files.setdefault(str(package_share), []).append(str(package_xml))

    # Install a generated ROS 2 ament index marker file.
    marker = _ensure_ament_resource_marker()
    data_files.setdefault(
        "share/ament_index/resource_index/packages", []
    ).append(str(marker))

    return sorted(data_files.items())


setup(data_files=_build_data_files())
