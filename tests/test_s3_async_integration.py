'''Perform an integration test with the S3 Async library.

This requires Python 3.5+ as the async/await capabilities are unavailable
in earlier versions.

Set environment variables for the proper settings for the account to test.
Use your own account credentials - these are examples and don't work.
  export test_storage__aws__access_key=abc
  export test_storage__aws__secret_key=123
  export test_storage__aws__bucket_name=TestAttachments

To test with a custom server or non-AWS service:
  export test_storage__aws__is_secure=false
  export test_storage__aws__host=localhost
  export test_storage__aws__port=5000

To test with AWS:
  export test_storage__aws__region=eu-west-1


Run this test with:
  pytest --s3-integration
'''

import io
import os

import pytest

from pyramid_storage import s3_async as s3

KEY_PREFIX = 'test_storage.'


@pytest.fixture
def s3_settings():
    # For testing, set variables in the environment with a
    # "test_storage__" prefix
    env_key_prefix = KEY_PREFIX.replace('.', '__')
    return {
        key.replace('__', '.'): value
        for key, value in os.environ.items()
        if key.startswith(env_key_prefix)
    }


@pytest.mark.s3_integration
@pytest.mark.asyncio
async def test_s3_async_integration(s3_settings):
    inst = s3.S3AsyncFileStorage.from_settings(s3_settings, KEY_PREFIX)

    test_filename = 'pyramid_storage_s3_async_test_file.txt'
    test_file_content = b'This is a test file\n'
    test_file = io.BytesIO(test_file_content)

    assert not await inst.exists(test_filename)

    # Create the file
    await inst.save_file(test_file, test_filename)
    assert await inst.exists(test_filename)

    # Read the file
    async with inst.s3_resource() as s3_resource:
        bucket = await inst.get_bucket(s3_resource)
        returned_file_content = io.BytesIO()
        await bucket.download_fileobj(test_filename, returned_file_content)

    assert test_file_content == returned_file_content.getvalue()

    # Delete the file
    await inst.delete(test_filename)
    assert not await inst.exists(test_filename)
