# -*- coding: utf-8 -*-

import re

import mock
import pytest

from pyramid import compat
from pyramid import exceptions as pyramid_exceptions


class MockBucket(mock.Mock):

    def list(self, prefix, delimiter):

        mock_key_1 = mock.Mock
        mock_key_1.name = 'image1.png'

        return [mock_key_1]

class MockS3Resource(object):

    def Bucket(self, bucket_name):
        return MockBucket()


def _get_mock_s3_resource(self):
    return MockS3Resource()


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


def test_save_if_file_not_allowed():
    from pyramid_storage import s3v2
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.zip"

    settings = {
                'storage.aws.access_key': 'abc',
                'storage.aws.secret_key': '123',
                'storage.aws.bucket_name': 'Attachments',
                'storage.aws.is_secure': 'false',
                'storage.aws.host': 'localhost',
                'storage.aws.port': '5000',
                'storage.aws.use_path_style': 'true',
                'storage.aws.num_retries': '3',
                'storage.aws.timeout': '10',
                'storage.aws.signature_version': 's3v4',
                'storage.aws.extensions': 'documents'
    }

    s = s3v2.S3V2FileStorage.from_settings(settings, 'storage.')

    with mock.patch(
            'pyramid_storage.s3v2.S3V2FileStorage.get_resource',
            _get_mock_s3_resource):

        with pytest.raises(FileNotAllowed):
            s.save(fs)


def test_save_if_file_allowed():
    from pyramid_storage import s3v2

    fs = mock.Mock()
    fs.filename = "test.jpeg"

    settings = {
                'storage.aws.access_key': 'abc',
                'storage.aws.secret_key': '123',
                'storage.aws.bucket_name': 'Attachments',
                'storage.aws.is_secure': 'false',
                'storage.aws.host': 'localhost',
                'storage.aws.port': '5000',
                'storage.aws.use_path_style': 'true',
                'storage.aws.num_retries': '3',
                'storage.aws.timeout': '10',
                'storage.aws.signature_version': 's3v4',
                'storage.aws.extensions': 'default'
            }
    s = s3v2.S3V2FileStorage.from_settings(settings, 'storage.')

    with mock.patch(
            'pyramid_storage.s3v2.S3V2FileStorage.get_resource',
            _get_mock_s3_resource):

        s.save(fs)


def test_save_file():
    from pyramid_storage import s3v2

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
        'storage.aws.is_secure': 'false',
        'storage.aws.host': 'localhost',
        'storage.aws.port': '5000',
        'storage.aws.use_path_style': 'true',
        'storage.aws.num_retries': '3',
        'storage.aws.timeout': '10',
        'storage.aws.signature_version': 's3v4',
        'storage.aws.extensions': 'default'
    }

    s = s3v2.S3V2FileStorage.from_settings(settings, 'storage.')

    with mock.patch(
            'pyramid_storage.s3v2.S3V2FileStorage.get_resource',
            _get_mock_s3_resource):
        name = s.save_file(mock.Mock(), "test.jpg")
        assert name == "test.jpg"


def test_save_if_randomize():
    from pyramid_storage import s3v2

    fs = mock.Mock()
    fs.filename = "test.jpg"

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
        'storage.aws.is_secure': 'false',
        'storage.aws.host': 'localhost',
        'storage.aws.port': '5000',
        'storage.aws.use_path_style': 'true',
        'storage.aws.num_retries': '3',
        'storage.aws.timeout': '10',
        'storage.aws.signature_version': 's3v4',
        'storage.aws.extensions': 'default'
    }

    s = s3v2.S3V2FileStorage.from_settings(settings, 'storage.')

    with mock.patch(
            'pyramid_storage.s3v2.S3V2FileStorage.get_resource',
            _get_mock_s3_resource):
        name = s.save(fs, randomize=True)
    assert name != "test.jpg"
