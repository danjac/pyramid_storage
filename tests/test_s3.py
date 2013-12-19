# -*- coding: utf-8 -*-

import os
import mock
import pytest

from pyramid import compat


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
