from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_release_publishes_every_installer_the_readme_tells_users_to_download():
    release = (ROOT / ".github/workflows/release.yml").read_text()
    readme = (ROOT / "README.md").read_text()
    for script in ("install.sh", "install-gui.sh"):
        if f"`{script}`" in readme or f"sh {script}" in readme:
            assert f"packaging/linux/{script}" in release, f"{script} is in the README but not in the release assets"
    assert (ROOT / "packaging/linux/install-gui.sh").exists()


def test_the_desktop_builds_bundle_the_package_data_so_the_icon_ships():
    text = (Path(__file__).parents[1] / ".github" / "workflows" / "release.yml").read_text()
    assert text.count("--collect-data live_bitcoin_tracker") == 3  # Linux, Windows and macOS desktop builds
    assert "packaging/linux/live-bitcoin-tracker.desktop" in text


def test_windows_file_properties_match_the_project_version_and_are_used_by_the_release():
    import re

    version = re.search(r'^version = "([^"]+)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
    info = (ROOT / "packaging" / "windows_version_info.txt").read_text()
    assert f"StringStruct('ProductVersion', '{version}')" in info and f"StringStruct('FileVersion', '{version}.0')" in info
    assert "StringStruct('ProductName', 'Live Bitcoin Tracker')" in info
    workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text()
    assert "--version-file packaging/windows_version_info.txt" in workflow
