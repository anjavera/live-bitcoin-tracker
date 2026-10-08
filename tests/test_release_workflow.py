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
