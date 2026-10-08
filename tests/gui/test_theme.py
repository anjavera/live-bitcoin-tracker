from live_bitcoin_tracker.gui import theme


def test_palette_values():
    assert theme.UP == "#00AE4B" and theme.DOWN == "#FE3D32"
    assert theme.BTC_ORANGE == "#F7931A" and theme.PAGE == "#0b0d12" and theme.CARD == "#1c1f27"
    assert theme.RADIUS == 20


def test_pick_fonts_prefers_polymarket_fonts():
    assert theme.pick_fonts(["Inter", "Instrument Sans Condensed", "Arial"]) == ("Instrument Sans Condensed", "Inter")


def test_pick_fonts_falls_back():
    assert theme.pick_fonts(["DejaVu Sans", "Arial"]) == ("DejaVu Sans", "DejaVu Sans")
    assert theme.pick_fonts(["Segoe UI"]) == ("Segoe UI", "Segoe UI")
    assert theme.pick_fonts([]) == ("", "")


def test_stylesheet_mentions_palette():
    css = theme.stylesheet()
    assert theme.PAGE in css and theme.CARD in css and "20px" in css


def test_load_bundled_fonts_without_directory_is_empty(tmp_path):
    assert theme.load_bundled_fonts(tmp_path / "nope") == []
