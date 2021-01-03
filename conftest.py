import pytest


def pytest_addoption(parser):
    # Add an option to run the S3 integration tests, and have them normally
    # skipped.
    parser.addoption(
        '--s3-integration',
        action='store_true',
        default=False,
        help='run the integration tests',
    )


def pytest_configure(config):
    config.addinivalue_line(
        'markers', 'integration: mark the test as an integration test'
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption('--s3-integration'):
        # Run the integration tests
        return

    integration_skip = pytest.mark.skip(
        reason='use --s3-integration option to run'
    )
    for item in items:
        if 's3_integration' in item.keywords:
            item.add_marker(integration_skip)
