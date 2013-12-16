import os
import mock
import pytest


def _mock_open_name():
    from pyramid_storage import _compat

    if _compat.PY3:
        return 'builtins.open'
    else:
        return '__builtin__.open'


def _mock_open(name='test', mode='wb'):

    obj = mock.Mock()
    obj.__enter__ = mock.Mock()
    obj.__enter__.return_value = mock.Mock()
    obj.__exit__ = mock.Mock()
    return obj


def test_resolve_extensions_if_individuals():
    from pyramid_storage import storage
    extensions = storage.resolve_extensions('txt jpg')
    assert 'jpg' in extensions
    assert 'txt' in extensions


def test_resolve_extensions_if_known_group():
    from pyramid_storage import storage
    extensions = storage.resolve_extensions('images')
    assert 'jpg' in extensions


def test_resolve_extensions_if_two_groups():
    from pyramid_storage import storage
    extensions = storage.resolve_extensions('images+video')
    assert 'jpg' in extensions
    assert 'wmv' in extensions


def test_resolve_extensions_if_mix():
    from pyramid_storage import storage
    extensions = storage.resolve_extensions('images+video+txt doc')
    assert 'jpg' in extensions
    assert 'wmv' in extensions
    assert 'txt' in extensions
    assert 'doc' in extensions


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import storage
    assert storage.FileStorage("").extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import storage
    assert not storage.FileStorage("").extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import storage
    assert not storage.FileStorage("").extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = storage.FileStorage("", extensions="images")

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = storage.FileStorage("", extensions="documents")

    assert not s.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = storage.FileStorage("", extensions="documents")

    with pytest.raises(storage.FileNotAllowed):
        s.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import storage, _compat

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = storage.FileStorage("uploads", extensions="images")

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


def test_save_if_randomize():
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = storage.FileStorage("uploads", extensions="images")

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
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = storage.FileStorage("uploads", extensions="images")

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


def test_random_filename():
    from pyramid_storage import storage
    filename = storage.random_filename("my little pony.png")
    assert filename.endswith(".png")
    assert filename != "my little pony.png"


def test_url():
    from pyramid_storage import storage
    s = storage.FileStorage("", "http://localhost/")
    assert s.url("test.jpg") == "http://localhost/test.jpg"


def test_path():
    from pyramid_storage import storage
    s = storage.FileStorage("uploads")
    assert s.path("test.jpg") == "uploads" + os.path.sep + "test.jpg"


def test_remove_if_exists():
    from pyramid_storage import storage

    patches = (
        mock.patch('os.remove', mock.Mock()),
        mock.patch('os.path.exists', lambda p: True),
    )

    for patch in patches:
        patch.start()

    s = storage.FileStorage("")
    assert s.delete("test.jpg")


def test_remove_if_not_exists():
    from pyramid_storage import storage

    s = storage.FileStorage("")

    with mock.patch('os.path.exists', lambda p: False):
        assert not s.delete("test.jpg")


def test_resolve_name_if_not_exists():
    from pyramid_storage import storage
    s = storage.FileStorage("uploads")

    with mock.patch("os.path.exists", lambda p: False):
        name, path = s.resolve_name("test.jpg", "uploads")
        assert name == "test.jpg"
        assert path == "uploads" + os.path.sep + "test.jpg"


def test_resolve_name_if_exists():
    from pyramid_storage import storage
    s = storage.FileStorage("uploads")

    def conditional_exists(path):
        return "1" not in path

    with mock.patch("os.path.exists", conditional_exists):
        name, path = s.resolve_name("test.jpg", "uploads")
        assert name == "test-1.jpg"
        assert path == "uploads" + os.path.sep + "test-1.jpg"


def test_dummy_storage():
    from pyramid_storage import storage

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = storage.DummyFileStorage()
    name = s.save(fs)
    assert name == "test.jpg"
    assert name in s.saved


def test_from_settings_with_defaults():

    from pyramid_storage import storage

    settings = {'storage.base_path': 'here'}
    inst = storage.FileStorage.from_settings(settings, 'storage.')
    assert inst.base_path == 'here'
    assert inst.base_url == ''
    assert set(('jpg', 'txt', 'doc')).intersection(inst.extensions)


def test_from_settings_if_base_path_missing():

    from pyramid_storage import storage

    with pytest.raises(ValueError):
        storage.FileStorage.from_settings({}, 'storage.')


def test_secure_filename():

    from pyramid_storage import _compat
    from pyramid_storage.storage import secure_filename
    assert secure_filename('My cool movie.mov') == 'My_cool_movie.mov'
    assert secure_filename('../../../etc/passwd') == 'etc_passwd'

    if _compat.PY3:
        target = 'i_contain_cool_umlauts.txt'
    else:
        target = 'i_contain_cool_mluts.txt'

    assert secure_filename(
        'i contain cool \xfcml\xe4uts.txt') == target
