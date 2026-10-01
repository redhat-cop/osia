"""AWS credential selection across configuration, clients and installer processes."""
from os import environ
from unittest import mock

import pytest
from dynaconf import Dynaconf  # type: ignore[import-untyped]

from osia import cli
from osia.config import config
from osia.installer import executor
from osia.installer.clouds.aws import AWSInstaller
from osia.installer.dns.route53 import Route53Provider


@pytest.fixture
def aws_settings(tmp_path, monkeypatch):
    """Load real YAML settings and a credentials file without using the user's AWS files."""
    monkeypatch.chdir(tmp_path)
    credentials = tmp_path / 'credentials'
    credentials.write_text(
        '[default]\naws_access_key_id = test-key\n'
        'aws_secret_access_key = test-secret\naws_session_token = test-token\n',
        encoding='utf-8',
    )
    settings_file = tmp_path / 'settings.yaml'
    settings_file.write_text(
        'default:\n'
        '  cloud:\n'
        '    aws:\n'
        '      cloud_env: test\n'
        '      environments:\n'
        '        - name: test\n'
        '          base_domain: example.com\n'
        '          credentials_file: credentials\n',
        encoding='utf-8',
    )
    monkeypatch.setattr(config, 'settings', Dynaconf(
        environments=True, env='default', load_dotenv=False, settings_files=[str(settings_file)],
    ))
    monkeypatch.delenv('AWS_SHARED_CREDENTIALS_FILE', raising=False)
    return credentials


def _parse_args(operation, *extra):
    return cli._setup_parser().parse_args([  # pylint: disable=protected-access
        operation, '--cluster-name', 'test-cluster', '--installer', 'openshift-install',
        '--skip-git', *extra,
    ])


@pytest.mark.parametrize('operation', ['install', 'clean'])
@pytest.mark.parametrize('override', [False, True])
def test_credentials_from_settings_and_cli(aws_settings, operation, override):
    """The CLI overrides YAML, and both install and clean resolve credentials."""
    extra = ['--cloud', 'aws', '--cloud-env', 'test']
    expected_file = aws_settings
    expected_key = 'test-key'
    expected_token: str | None = 'test-token'
    if override:
        expected_file = aws_settings.with_name('override')
        expected_file.write_text(
            '[default]\naws_access_key_id = override-key\naws_secret_access_key = test-secret\n',
            encoding='utf-8',
        )
        extra += ['--credentials-file', str(expected_file)]
        expected_key = 'override-key'
        expected_token = None

    result = config.read_config(_parse_args(operation, *extra), cli.ARGUMENTS)

    assert result['dns'] is None
    assert result['cloud']['credentials_file'] == str(expected_file)
    assert result['cloud']['aws_access_key_id'] == expected_key
    assert result['cloud']['aws_secret_access_key'] == 'test-secret'
    assert result['cloud']['aws_session_token'] == expected_token
    assert 'AWS_SHARED_CREDENTIALS_FILE' not in environ


@pytest.mark.parametrize('provider', ['aws', 'route53'])
def test_temporary_credentials_reach_aws_clients(aws_settings, provider):
    """Both EC2 and Route53 requests retain the session token from the file."""
    args = _parse_args('install', '--cloud', 'aws')
    if provider == 'route53':
        config.settings.set('DNS', {'route53': {'credentials_file': str(aws_settings), 'ttl': 60}})
        args.dns_provider = 'route53'
    result = config.read_config(args, cli.ARGUMENTS)
    with mock.patch('boto3.client') as client:
        if provider == 'aws':
            client.return_value.describe_vpcs.return_value = {'Vpcs': []}
            client.return_value.get_service_quota.return_value = {'Quota': {'Value': 5}}
            installer = AWSInstaller(list_of_regions=['us-east-1'], **result['cloud'])
            installer.acquire_resources()
            assert installer.cluster_region == 'us-east-1'
        else:
            client.return_value.list_hosted_zones.return_value = {
                'HostedZones': [{'Name': 'example.com.', 'Id': 'test-zone'}],
            }
            dns_settings = result.get('dns')
            assert dns_settings is not None
            dns = Route53Provider(**dns_settings['conf'])
            dns.add_api_domain(mock.Mock(get_api_ip=mock.Mock(return_value='192.0.2.1')))
            client.return_value.change_resource_record_sets.assert_called_once()

    assert client.call_count > 0
    for call in client.call_args_list:
        assert call.kwargs == {
            'aws_access_key_id': 'test-key',
            'aws_secret_access_key': 'test-secret',
            'aws_session_token': 'test-token',
        }


@pytest.mark.parametrize(('operation', 'returncodes', 'expected_operations'), [
    ('install', [0], ['create']),
    ('install', [1, 1, 0], ['create', 'destroy', 'destroy']),
    ('clean', [1, 0], ['destroy', 'destroy']),
])
def test_credentials_reach_installer_and_cleanup(aws_settings, operation, returncodes, expected_operations):
    """YAML credentials reach every subprocess, including failed-install cleanup and retries."""
    processes = [mock.MagicMock() for _ in returncodes]
    for process, returncode in zip(processes, returncodes):
        process.__enter__.return_value.returncode = returncode
    args = _parse_args(operation, '--cloud', 'aws')
    with mock.patch.object(AWSInstaller, 'acquire_resources'), \
            mock.patch.object(AWSInstaller, 'process_template'), \
            mock.patch.object(executor, 'Popen', side_effect=processes) as popen:
        args.func(args)

    assert [call.args[0][1] for call in popen.call_args_list] == expected_operations
    for call in popen.call_args_list:
        assert call.kwargs['env']['AWS_SHARED_CREDENTIALS_FILE'] == str(aws_settings)
        assert call.kwargs['env']['AWS_PROFILE'] == 'default'
    assert 'AWS_SHARED_CREDENTIALS_FILE' not in environ


def test_clean_with_explicit_credentials_without_cloud(aws_settings):
    """Clean also accepts a credentials file without selecting a cloud environment."""
    args = _parse_args('clean', '--credentials-file', str(aws_settings))
    with mock.patch.object(cli, 'delete_cluster') as delete:
        args.func(args)
    delete.assert_called_once_with('test-cluster', 'openshift-install', credentials_file=str(aws_settings))


@pytest.mark.parametrize('credentials_file', [None, 'credentials'])
@pytest.mark.parametrize('os_image', [None, 'https://example.com/image'])
def test_installer_environment(monkeypatch, tmp_path, credentials_file, os_image):
    """Explicit files override ambient AWS credentials only in the child process."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('AWS_SHARED_CREDENTIALS_FILE', '/ambient/credentials')
    monkeypatch.setenv('AWS_PROFILE', 'ambient-profile')
    for key in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN'):
        monkeypatch.setenv(key, 'ambient-value')
    original_env = environ.copy()
    with mock.patch.object(executor, 'Popen') as popen:
        popen.return_value.__enter__.return_value.returncode = 0
        executor.execute_installer('openshift-install', 'test-cluster', 'create',
                                   os_image=os_image, credentials_file=credentials_file)

    expected_env = original_env.copy()
    if credentials_file:
        expected_env['AWS_SHARED_CREDENTIALS_FILE'] = str(tmp_path / credentials_file)
        expected_env['AWS_PROFILE'] = 'default'
        for key in ('AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_SECURITY_TOKEN'):
            del expected_env[key]
    if os_image:
        expected_env['OPENSHIFT_INSTALL_OS_IMAGE_OVERRIDE'] = os_image
    assert popen.call_args.kwargs['env'] == (expected_env if credentials_file or os_image else None)
    assert dict(environ) == original_env
