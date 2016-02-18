# -*- coding: utf-8 -*-

import os
import mock
import pytest

from pyramid import compat
from pyramid import exceptions as pyramid_exceptions


def _mock_open_name():

    if compat.PY3:
        return 'builtins.open'
    else:
        return '__builtin__.open'


def _mock_open(name='test', mode='wb'):

    obj = mock.Mock()
    obj.__enter__ = mock.Mock()
    obj.__enter__.return_value = mock.Mock()
    obj.__exit__ = mock.Mock()
    return obj


def test_extension_allowed_if_any():
    from pyramid_storage import local
    assert local.LocalFileStorage(
        "", extensions='any').extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import local
    assert local.LocalFileStorage("").extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import local
    assert not local.LocalFileStorage("").extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import local
    assert not local.LocalFileStorage("").extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import local

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = local.LocalFileStorage("", extensions="images")

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import local

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = local.LocalFileStorage("", extensions="documents")

    assert not s.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import local
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = local.LocalFileStorage("", extensions="documents")

    with pytest.raises(FileNotAllowed):
        s.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import local

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = local.LocalFileStorage("uploads", extensions="images")

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch("os.path.exists", lambda p: False),
        mock.patch("os.makedirs", lambda p: True),
        mock.patch("shutil.copyfileobj", lambda x, y: True),
    )

    for patch in patches:
        patch.start()

    name = s.save(fs)
    assert name == "test.jpg"

    for patch in patches:
        patch.stop()


def test_save_file():
    from pyramid_storage import local

    s = local.LocalFileStorage("uploads", extensions="images")

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch("os.path.exists", lambda p: False),
        mock.patch("os.makedirs", lambda p: True),
        mock.patch("shutil.copyfileobj", lambda x, y: True),
    )

    for patch in patches:
        patch.start()

    name = s.save_file(mock.Mock(), "test.jpg", replace=True)
    assert name == "test.jpg"

    for patch in patches:
        patch.stop()


def test_save_filename():
    from pyramid_storage import local

    s = local.LocalFileStorage("uploads", extensions="images")

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch("os.path.exists", lambda p: False),
        mock.patch("os.makedirs", lambda p: True),
        mock.patch("shutil.copyfileobj", lambda x, y: True),
    )

    for patch in patches:
        patch.start()

    name = s.save_filename("test.jpg")
    assert name == "test.jpg"

    for patch in patches:
        patch.stop()


def test_save_if_randomize():
    from pyramid_storage import local

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = local.LocalFileStorage("uploads", extensions="images")

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch("os.path.exists", lambda p: False),
        mock.patch("os.makedirs", lambda p: True),
        mock.patch("shutil.copyfileobj", lambda x, y: True),
    )

    for patch in patches:
        patch.start()

    name = s.save(fs, randomize=True)
    assert name != "test.jpg"
    assert name.endswith(".jpg")

    for patch in patches:
        patch.stop()


def test_save_in_folder():
    from pyramid_storage import local

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = local.LocalFileStorage("uploads", extensions="images")

    patches = (
        mock.patch(_mock_open_name()), _mock_open(),
        mock.patch("os.path.exists", lambda p: False),
        mock.patch("os.makedirs", lambda p: True),
        mock.patch("shutil.copyfileobj", lambda x, y: True),
    )

    for patch in patches:
        patch.start()

    name = s.save(fs, folder="photos")
    assert name == "photos%stest.jpg" % os.path.sep

    for patch in patches:
        patch.stop()


def test_url():
    from pyramid_storage import local
    s = local.LocalFileStorage("", "http://localhost/")
    assert s.url("test.jpg") == "http://localhost/test.jpg"


def test_path():
    from pyramid_storage import local
    s = local.LocalFileStorage("uploads")
    assert s.path("test.jpg") == "uploads" + os.path.sep + "test.jpg"


def test_remove_if_exists():
    from pyramid_storage import local

    patches = (
        mock.patch('os.remove', mock.Mock()),
        mock.patch('os.path.exists', lambda p: True),
    )

    for patch in patches:
        patch.start()

    s = local.LocalFileStorage("")
    assert s.delete("test.jpg")


def test_remove_if_not_exists():
    from pyramid_storage import local

    s = local.LocalFileStorage("")

    with mock.patch('os.path.exists', lambda p: False):
        assert not s.delete("test.jpg")


def test_resolve_name_if_not_exists():
    from pyramid_storage import local
    s = local.LocalFileStorage("uploads")

    with mock.patch("os.path.exists", lambda p: False):
        name, path = s.resolve_name("test.jpg", "uploads")
        assert name == "test.jpg"
        assert path == "uploads" + os.path.sep + "test.jpg"


def test_resolve_name_if_exists():
    from pyramid_storage import local
    s = local.LocalFileStorage("uploads")

    def conditional_exists(path):
        return "1" not in path

    with mock.patch("os.path.exists", conditional_exists):
        name, path = s.resolve_name("test.jpg", "uploads")
        assert name == "test-1.jpg"
        assert path == "uploads" + os.path.sep + "test-1.jpg"


def test_dummy_storage():
    from pyramid_storage import testing

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = testing.DummyFileStorage()
    name = s.save(fs)
    assert name == "test.jpg"
    assert name in s.saved


def test_from_settings_with_defaults():

    from pyramid_storage import local

    settings = {'storage.base_path': 'here'}
    inst = local.LocalFileStorage.from_settings(settings, 'storage.')
    assert inst.base_path == 'here'
    assert inst.base_url == ''
    assert set(('jpg', 'txt', 'doc')).intersection(inst.extensions)


def test_from_settings_if_base_path_missing():

    from pyramid_storage import local

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        local.LocalFileStorage.from_settings({}, 'storage.')
