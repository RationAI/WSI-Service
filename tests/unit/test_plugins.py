from wsi_service.plugins import plugins


def test_check_available_base_plugins():
    assert len(plugins) >= 4
    assert "openslide" in plugins.keys()
    assert "pil" in plugins.keys()
    assert "tifffile" in plugins.keys()
    assert "wsidicom" in plugins.keys()
