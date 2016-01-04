# -*- coding: utf-8 -*-

import mock
import pytest

from pyramid import compat
from pyramid import exceptions as pyramid_exceptions


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


def test_from_settings_with_defaults():

    from pyramid_storage import s3

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
    }
    inst = s3.S3FileStorage.from_settings(settings, 'storage.')
    assert inst.base_url == ''
    assert inst.bucket_name == 'Attachments'
    assert inst.acl == 'public-read'
    assert inst.conn_options['aws_access_key_id'] == 'abc'
    assert inst.conn_options['aws_secret_access_key'] == '123'
    assert set(('jpg', 'txt', 'doc')).intersection(inst.extensions)

    with mock.patch('boto.connect_s3') as boto_mocked:
        boto_mocked.return_value.http_connection_kwargs = {}
        inst.get_connection()
        _, boto_options = boto_mocked.call_args_list[0]
        assert 'host' not in boto_options
        assert 'port' not in boto_options


def test_from_settings_if_base_path_missing():

    from pyramid_storage import s3

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        s3.S3FileStorage.from_settings({}, 'storage.')


def test_from_settings_with_additional_options():

    from pyramid_storage import s3

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
    }
    inst = s3.S3FileStorage.from_settings(settings, 'storage.')
    with mock.patch('boto.connect_s3') as boto_mocked:
        boto_mocked.return_value.http_connection_kwargs = {}
        conn = inst.get_connection()
        assert conn.num_retries == 3
        assert conn.http_connection_kwargs['timeout'] == 10

        _, boto_options = boto_mocked.call_args_list[0]

        calling_format = boto_options.pop('calling_format')
        assert calling_format.__class__.__name__ == 'OrdinaryCallingFormat'

        assert boto_options == {
            'is_secure': False,
            'host': 'localhost',
            'port': 5000,
            'aws_access_key_id': 'abc',
            'aws_secret_access_key': '123'
        }


def test_from_settings_with_regional_options_ignores_host_port():

    from pyramid_storage import s3

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
        'storage.aws.region': 'eu-west-1',
        'storage.aws.host': 'localhost',
        'storage.aws.port': '5000',
    }
    inst = s3.S3FileStorage.from_settings(settings, 'storage.')
    with mock.patch('boto.s3.connect_to_region') as boto_mocked:
        boto_mocked.return_value.http_connection_kwargs = {}
        inst.get_connection()
        _, boto_options = boto_mocked.call_args_list[0]
        assert 'host' not in boto_options
        assert 'port' not in boto_options
