# -*- coding: utf-8 -*-

import re

import mock
import pytest

from pyramid import compat


class MockS3Connection(object):

    def get_bucket(self, bucket_name):
        return mock.Mock()


def _get_mock_s3_connection(self):
    return MockS3Connection()


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
    from pyramid_storage import s3
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="any")
    assert s.extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="images")
    assert s.extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="images")
    assert not s.extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import s3
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="images")
    assert not s.extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="images")

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="documents")

    assert not s.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import s3
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(access_key="AK",
                         secret_key="SK",
                         bucket_name="my_bucket",
                         extensions="documents")

    with pytest.raises(FileNotAllowed):
        s.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):
        name = s.save(fs)
    assert name == "test.jpg"


def test_save_file():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):
        name = s.save_file(mock.Mock(), "test.jpg")
    assert name == "test.jpg"


def test_save_filename():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    patches = (
        mock.patch(_mock_open_name(), _mock_open),
        mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection
        )
    )

    for patch in patches:
        patch.start()

    name = s.save_filename("test.jpg")
    assert name == "test.jpg"

    for patch in patches:
        patch.stop()


def test_save_if_randomize():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):
        name = s.save(fs, randomize=True)
    assert name != "test.jpg"


def test_save_in_folder():

    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):
        name = s.save(fs, folder="my_folder")
    assert name == "my_folder/test.jpg"


def test_save_in_folder_with_subdir():

    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):
        name = s.save(fs, folder="my_folder", partition_sub_dir=True)

    regex = re.compile('my_folder/[a-f-0-9]+/test.jpg')

    assert regex.match(name) is not None


def test_delete():

    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images")

    with mock.patch(
            'pyramid_storage.s3.S3FileStorage.get_connection',
            _get_mock_s3_connection):

        s.delete("test.jpg")
