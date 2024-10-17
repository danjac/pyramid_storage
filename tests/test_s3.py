# -*- coding: utf-8 -*-

from unittest import mock

import pytest
from pyramid import exceptions as pyramid_exceptions


@pytest.fixture
def mock_s3_client():
    with mock.patch("pyramid_storage.s3.S3FileStorage.s3_client") as mocked:
        yield mocked


def test_extension_allowed_if_any():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="any"
    )
    assert s.extension_allowed(".jpg")


def test_extension_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )
    assert s.extension_allowed(".jpg", ("jpg",))


def test_extension_not_allowed_if_allowed_if_dotted():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )
    assert not s.extension_allowed("jpg", ("gif",))


def test_extension_not_allowed_if_allowed_if_not_dotted():
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )
    assert not s.extension_allowed("jpg", ("gif",))


def test_file_allowed():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    assert s.file_allowed(fs)


def test_file_not_allowed():
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="documents"
    )

    assert not s.file_allowed(fs)


def test_save_if_file_not_allowed():
    from pyramid_storage import s3
    from pyramid_storage.exceptions import FileNotAllowed

    fs = mock.Mock()
    fs.filename = "test.jpg"
    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="documents"
    )

    with pytest.raises(FileNotAllowed):
        s.save(fs)


def test_save_if_file_allowed(mock_s3_client):
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    name = s.save(fs)
    assert name == "test.jpg"


def test_save_file(mock_s3_client):
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    name = s.save_file(mock.Mock(), "test.jpg")
    assert name == "test.jpg"


def test_save_filename(mock_s3_client, tmp_path):
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    p = tmp_path / "hello.jpg"
    p.write_text("test")

    name = s.save_filename(str(p))
    assert name == "hello.jpg"


def test_save_if_randomize(mock_s3_client):
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    name = s.save(fs, randomize=True)

    assert name != "test.jpg"


def test_save_in_folder(mock_s3_client):
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.jpg"

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    name = s.save(fs, folder="my_folder")

    assert name == "my_folder/test.jpg"


def test_save_with_content_type(mock_s3_client):
    from pyramid_storage import s3

    fs = mock.Mock()
    fs.filename = "test.doc"

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="documents"
    )

    s.save(fs, headers={"Content-Type": "text/html"})

    assert mock_s3_client.put_object(
        Bucket="my_bucket", Key="test.doc", Body=mock.ANY, ACL=None, ContentType="text/html"
    )


def test_delete(mock_s3_client):
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    s.delete("test.jpg")

    assert mock_s3_client.delete_object(Bucket="my_bucket", Key="test.jpg")


def test_from_settings_with_defaults():
    from pyramid_storage import s3

    settings = {
        "storage.aws.access_key": "abc",
        "storage.aws.secret_key": "123",
        "storage.aws.bucket_name": "Attachments",
        "storage.aws.region": "us2",
    }
    inst = s3.S3FileStorage.from_settings(settings, "storage.")
    assert inst.base_url == ""
    assert inst.bucket_name == "Attachments"
    assert inst.acl == "public-read"
    assert inst.conn_options["aws_access_key_id"] == "abc"
    assert inst.conn_options["aws_secret_access_key"] == "123"
    assert set(("jpg", "txt", "doc")).intersection(inst.extensions)

    with mock.patch("boto3.client") as boto_mocked:
        inst.s3_client

        boto_mocked.assert_called_with(
            "s3",
            config=mock.ANY,
            aws_access_key_id="abc",
            aws_secret_access_key="123",
            region_name="us2",
        )
        call = boto_mocked.call_args_list[0]
        _, kwargs = call
        assert kwargs["config"].connect_timeout == 5


def test_from_settings_if_base_path_missing():
    from pyramid_storage import s3

    with pytest.raises(pyramid_exceptions.ConfigurationError):
        s3.S3FileStorage.from_settings({}, "storage.")


def test_from_settings_with_additional_options():
    from pyramid_storage import s3

    settings = {
        "storage.aws.access_key": "abc",
        "storage.aws.secret_key": "123",
        "storage.aws.bucket_name": "Attachments",
        "storage.aws.is_secure": "false",
        "storage.aws.host": "localhost",
        "storage.aws.port": "5000",
        "storage.aws.use_path_style": "true",
        "storage.aws.num_retries": "3",
        "storage.aws.timeout": "10",
    }
    inst = s3.S3FileStorage.from_settings(settings, "storage.")

    with mock.patch("boto3.client") as boto_mocked:
        inst.s3_client

        boto_mocked.assert_called_with(
            "s3",
            config=mock.ANY,
            aws_access_key_id="abc",
            aws_secret_access_key="123",
            endpoint="http://localhost:5000",
        )
        call = boto_mocked.call_args_list[0]
        _, kwargs = call
        assert kwargs["config"].connect_timeout == 10.0
        assert kwargs["config"].retries == {"max_attempts": 3, "mode": "standard"}
        assert kwargs["config"].s3 == {"addressing_style": "path"}


def test_from_settings_with_regional_options_ignores_host_port():
    from pyramid_storage import s3

    settings = {
        "storage.aws.access_key": "abc",
        "storage.aws.secret_key": "123",
        "storage.aws.bucket_name": "Attachments",
        "storage.aws.region": "eu-west-1",
        "storage.aws.host": "localhost",
        "storage.aws.port": "5000",
    }
    inst = s3.S3FileStorage.from_settings(settings, "storage.")
    with mock.patch("boto3.client") as boto_mocked:
        inst.s3_client

        boto_mocked.assert_called_with(
            "s3",
            config=mock.ANY,
            aws_access_key_id="abc",
            aws_secret_access_key="123",
            region_name="eu-west-1",
        )


def test_save_file_to_bucket(mock_s3_client):
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    s.save_file(mock.Mock(), "test.jpg")

    mock_s3_client.put_object(
        Bucket="my_bucket", Key="test.jpg", Body=mock.ANY, ACL=None, ContentType="image/jpeg"
    )

    s.save_file(mock.Mock(), "test.jpg", bucket_name="other_bucket")

    mock_s3_client.put_object(
        Bucket="other_bucket", Key="test.jpg", Body=mock.ANY, ACL=None, ContentType="image/jpeg"
    )


def test_delete_from_bucket(mock_s3_client):
    from pyramid_storage import s3

    s = s3.S3FileStorage(
        access_key="AK", secret_key="SK", bucket_name="my_bucket", extensions="images"
    )

    s.delete("test.jpg")

    mock_s3_client.delete_object(Bucket="my_bucket", Key="test.jpg")

    s.delete("test.jpg", bucket_name="other_bucket")

    mock_s3_client.delete_object(Bucket="other_bucket", Key="test.jpg")
