from wsi_service.plugins import plugins


def test_check_available_base_plugins():
    assert len(plugins) >= 2
    assert "tifffile" in plugins.keys()
    assert "openslide" in plugins.keys()
