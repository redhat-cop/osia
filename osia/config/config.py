"""
Module implements merging of default configuration obtained via Dynaconf
with command line arguments.
"""
import argparse
import configparser
import logging
import warnings
from pathlib import Path

from dynaconf import Dynaconf  # type: ignore[import-untyped]

ARCH_AMD = "amd64"
ARCH_X86_64 = "x86_64"
ARCH_ARM = "arm64"
ARCH_AARCH64 = "aarch64"
ARCH_PPC = "ppc64le"
ARCH_S390X = "s390x"

settings = Dynaconf(
    environments=True,
    lowercase_read=False,
    load_dotenv=True,
    settings_files=[name + end for name in ["settings", ".secrets"] for end in [".yaml", ".yml"]]
)


def _resolve_cloud_name(args: argparse.Namespace) -> dict | None:
    defaults = settings.as_dict()

    if defaults['CLOUD'][args.cloud].get('environments', None) is None:
        warnings.warn('[DEPRECATION WARNING] The structure of settings.yaml is changed, '
                      'please use environments list and cloud_env option. This behavior will be '
                      'removed in future releases.')
        return defaults['CLOUD'][args.cloud]
    default_env = defaults['CLOUD'][args.cloud].get('cloud_env', None) \
        if args.cloud_env is None else \
        args.cloud_env
    if default_env is None:
        logging.error("Couldn't resolve default environment")
        raise Exception("Invalid environment setup, cloud_env is missing")
    for env in defaults['CLOUD'][args.cloud]['environments']:
        if env['name'] == default_env:
            return env
    logging.warning("No environment found, maybe all variables are passed from command line")
    return None


def _read_aws_credentials(configuration: dict) -> None:
    """Load the default profile and normalize its path for the installer."""
    credentials_file = Path(configuration['credentials_file']).expanduser().resolve()
    config = configparser.ConfigParser(interpolation=None)
    with credentials_file.open(encoding='utf-8') as credentials:
        config.read_file(credentials)
    profile = config['default']
    configuration.update({
        'credentials_file': str(credentials_file),
        'aws_access_key_id': profile['aws_access_key_id'],
        'aws_secret_access_key': profile['aws_secret_access_key'],
        'aws_session_token': profile.get('aws_session_token'),
    })


def read_config(args: argparse.Namespace, default_args: dict) -> dict:
    """
    Reads config from Dynaconf and merges it with arguments provided via commandline.
    """
    result = {'cloud': {},
              'dns': None,
              'cloud_name': {},
              'cluster_name': args.cluster_name}
    if 'cloud' not in args:
        return result
    defaults = settings.as_dict()
    dns_conf = None

    if getattr(args, 'dns_provider', None) is not None:
        dns_conf = defaults['DNS'][args.dns_provider]
        result['dns'] = {'provider': args.dns_provider,
                         'conf': dns_conf}
        dns_conf.update(
            {j[4:]: i['proc'](vars(args)[j])
             for j, i in default_args['dns'].items()
             if vars(args)[j] is not None}
        )
        if dns_conf.get('credentials_file'):
            _read_aws_credentials(dns_conf)

    if args.cloud is not None:
        cloud_defaults = _resolve_cloud_name(args)
        result['cloud_name'] = args.cloud
        result['cloud'] = cloud_defaults or {}
        result['cloud'].update(
            {j: i['proc'](vars(args)[j]) for j, i in default_args['install'].items()
             if vars(args).get(j) is not None}
        )

        if dns_conf is not None:
            dns_conf.update({
                'cluster_name': args.cluster_name,
                'base_domain': result['cloud']['base_domain']
            })

    if getattr(args, 'credentials_file', None) is not None:
        result['cloud']['credentials_file'] = args.credentials_file
    if result['cloud'].get('credentials_file'):
        _read_aws_credentials(result['cloud'])
    return result
