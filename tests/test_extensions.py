# -*- coding: utf-8 -*-


def test_resolve_extensions_if_individuals():
    from pyramid_storage.extensions import resolve_extensions

    extensions = resolve_extensions("txt jpg")
    assert "jpg" in extensions
    assert "txt" in extensions


def test_resolve_extensions_if_known_group():
    from pyramid_storage.extensions import resolve_extensions

    extensions = resolve_extensions("images")
    assert "jpg" in extensions


def test_resolve_extensions_if_two_groups():
    from pyramid_storage.extensions import resolve_extensions

    extensions = resolve_extensions("images+video")
    assert "jpg" in extensions
    assert "wmv" in extensions


def test_resolve_extensions_if_mix():
    from pyramid_storage.extensions import resolve_extensions

    extensions = resolve_extensions("images+video+txt doc")
    assert "jpg" in extensions
    assert "wmv" in extensions
    assert "txt" in extensions
    assert "doc" in extensions
