# -*- coding: utf-8 -*-
import sys
import mock
import pytest

import botocore.exceptions

from pyramid import exceptions as pyramid_exceptions

pytestmark = pytest.mark.skipif(
    sys.version_info < (3, 5), reason='requires python3.5 or higher'
)

# Mock the AWS async resources that we'll be using
# AsyncMock is available in Python 3.8, but to keep things working with older
# versions, these explicit objects will provide the necessary mocking.


class MockS3AsyncObject:
    def __init__(self, bucket_name, filename):
        self._bucket_name = bucket_name
        self._filename = filename
        self._deleted = False

    async def delete(self):
        self._deleted = True


class MockS3AsyncBucket:
    def __init__(self, name):
        self._name = name
        self._upload_fileobj_file = None
        self._upload_fileobj_filename = None
        self._upload_fileobj_call_args = None

    async def upload_fileobj(self, file, filename, **kwargs):
        self._upload_fileobj_file = file
        self._upload_fileobj_filename = filename
        self._upload_fileobj_call_args = kwargs
        return None


class MockS3AsyncResource:
    def __init__(self):
        self._file_object = None
        self._bucket = None

    async def Object(self, bucket_name, filename):
        self._file_object = MockS3AsyncObject(bucket_name, filename)
        return self._file_object

    async def Bucket(self, bucket_name):
        self._bucket = MockS3AsyncBucket(bucket_name)
        return self._bucket


class MockS3AsyncClient:
    def __init__(self, make_object_missing=False):
        self._make_object_missing = make_object_missing
        self._head_object_kwargs = None

    async def head_object(self, **kwargs):
        self._head_object_kwargs = kwargs
        if self._make_object_missing:
            raise botocore.exceptions.ClientError(
                operation_name='head_object',
                error_response={
                    'Error': {'Code': '404'},
                },
            )


class MockAsyncContext:
    def __init__(self, item):
        self.item = item
        self.called = False

    async def __aenter__(self):
        self.called = True
        return self.item

    async def __aexit__(self, exc_type, exc, tb):
        assert not exc


@pytest.fixture
def mock_s3_client(mocker):
    client = MockS3AsyncClient()
    contextualized = MockAsyncContext(client)
    mocker.patch(
        'pyramid_storage.s3_async.S3AsyncFileStorage.s3_client',
        return_value=contextualized,
    )
    return client


@pytest.fixture
def mock_s3_client_failure(mocker):
    client = MockS3AsyncClient(make_object_missing=True)
    contextualized = MockAsyncContext(client)
    mocker.patch(
        'pyramid_storage.s3_async.S3AsyncFileStorage.s3_client',
        return_value=contextualized,
    )
    return client


@pytest.fixture
def mock_s3_resource(mocker):
    resource = MockS3AsyncResource()
    contextualized = MockAsyncContext(resource)
    mocker.patch(
        'pyramid_storage.s3_async.S3AsyncFileStorage.s3_resource',
        return_value=contextualized,
    )
    return resource


@pytest.fixture
def mock_async_open(mocker):
    mocker.patch(
        'pyramid_storage.s3_async.async_open', return_value=mock.Mock()
    )


def test_extension_allowed_if_any():
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="any",
    )
    assert s.extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )
    assert s.extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )
    assert not s.extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )
    assert not s.extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="documents",
    )

    assert not s.file_allowed(fs)


@pytest.mark.asyncio
async def test_save_if_file_not_allowed(mock_s3_resource):
    from pyramid_storage import s3_async as s3
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="documents",
    )

    with pytest.raises(FileNotAllowed):
        await s.save(fs)


@pytest.mark.asyncio
async def test_save_if_file_allowed(mock_s3_resource):
    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    name = await s.save(fs)
    assert name == "test.jpg"


@pytest.mark.asyncio
async def test_save_file(mock_s3_resource):
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    name = await s.save_file(mock.Mock(), "test.jpg")
    assert name == "test.jpg"


@pytest.mark.asyncio
async def test_save_filename(mock_s3_resource, mock_async_open):
    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    name = await s.save_filename("test.jpg")
    assert name == "test.jpg"


@pytest.mark.asyncio
async def test_save_if_randomize(mock_s3_resource):
    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    name = await s.save(fs, randomize=True)
    assert name != "test.jpg"


@pytest.mark.asyncio
async def test_save_in_folder(mock_s3_resource):

    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    name = await s.save(fs, folder="my_folder")
    assert name == "my_folder/test.jpg"


@pytest.mark.asyncio
async def test_save_with_content_type(mock_s3_resource):

    from pyramid_storage import s3_async as s3

    fs = mock.Mock()
    fs.filename = "test.doc"

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="documents",
    )

    await s.save(fs, headers={"Content-Type": "text/html"})

    call_args = mock_s3_resource._bucket._upload_fileobj_call_args
    assert call_args["ExtraArgs"]["ContentType"] == "text/html"


@pytest.mark.asyncio
async def test_delete(mock_s3_resource):

    from pyramid_storage import s3_async as s3

    s = s3.S3AsyncFileStorage(
        access_key="AK",
        secret_key="SK",
        bucket_name="my_bucket",
        extensions="images",
    )

    await s.delete("test.jpg")
    assert mock_s3_resource._file_object._deleted


def test_from_settings_with_defaults():

    from pyramid_storage import s3_async as s3

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
    }
    inst = s3.S3AsyncFileStorage.from_settings(settings, 'storage.')
    assert inst.base_url == ''
    assert inst.bucket_name == 'Attachments'
    assert inst.acl == 'public-read'
    assert inst.conn_options['aws_access_key_id'] == 'abc'
    assert inst.conn_options['aws_secret_access_key'] == '123'
    assert set(('jpg', 'txt', 'doc')).intersection(inst.extensions)


def test_from_settings_if_base_path_missing():

    from pyramid_storage import s3_async as s3

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        s3.S3AsyncFileStorage.from_settings({}, 'storage.')


def test_from_settings_with_additional_options():

    from pyramid_storage import s3_async as s3

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
        'storage.aws.is_secure': 'false',
        'storage.aws.host': 'localhost',
        'storage.aws.port': '5000',
        'storage.aws.use_path_style': 'true',
        'storage.aws.num_retries': '3',
        'storage.aws.timeout': '20',
        'storage.aws.read_timeout': '30',
        'storage.aws.keepalive_timeout': '2',
    }
    inst = s3.S3AsyncFileStorage.from_settings(settings, 'storage.')

    assert inst.conn_options['endpoint_url'] == 'http://localhost:5000'

    config = inst.conn_options['config']
    assert config.retries == {'max_attempts': 3}
    assert config.connect_timeout == 20.0
    assert config.read_timeout == 30.0
    assert config.connector_args == {'keepalive_timeout': 2.0}


def test_from_settings_with_regional_options_ignores_host_port():

    from pyramid_storage import s3_async as s3

    settings = {
        'storage.aws.access_key': 'abc',
        'storage.aws.secret_key': '123',
        'storage.aws.bucket_name': 'Attachments',
        'storage.aws.region': 'eu-west-1',
        'storage.aws.host': 'localhost',
        'storage.aws.port': '5000',
    }
    inst = s3.S3AsyncFileStorage.from_settings(settings, 'storage.')

    assert 'endpoint_url' not in inst.conn_options
