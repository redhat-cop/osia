"""
Module implements merging of default configuration obtained via Dynaconf
with command line arguments.
"""
import argparse
import configparser
import logging
import warnings

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


def read_config(args: argparse.Namespace, default_args: dict) -> dict:
    """
    Reads config from Dynaconf and merges it with arguments provided via commandline.
    """
    result = {'cloud': {},
              'dns': {},
              'cloud_name': {},
              'cluster_name': args.cluster_name}
    if 'cloud' not in args:
        return result
    defaults = settings.as_dict()

    if args.dns_provider is not None:
        result['dns'] = {'provider': args.dns_provider,
                         'conf': defaults['DNS'][args.dns_provider]}
        result['dns']['conf'].update(
            {j[4:]: i['proc'](vars(args)[j])
             for j, i in default_args['dns'].items()
             if vars(args)[j] is not None}
        )
        if 'credentials_file' in result['dns']['conf'].keys():
            config = configparser.ConfigParser()
            config.read(result['dns']['conf']['credentials_file'])

            result['dns']['conf'].update({
                "aws_access_key_id": config["default"]["aws_access_key_id"],
                "aws_secret_access_key": config["default"]["aws_secret_access_key"],
            })

    if args.cloud is not None:
        cloud_defaults = _resolve_cloud_name(args)
        result['cloud_name'] = args.cloud
        result['cloud'] = cloud_defaults
        result['cloud'].update(
            {j: i['proc'](vars(args)[j]) for j, i in default_args['install'].items()
             if vars(args)[j] is not None}
        )

        if 'credentials_file' in result['cloud']:
            config = configparser.ConfigParser()
            config.read(result['cloud']['credentials_file'])

            result['cloud'].update({
                "aws_access_key_id": config["default"]["aws_access_key_id"],
                "aws_secret_access_key": config["default"]["aws_secret_access_key"],
            })

        if result['dns'] is not None:
            result['dns']['conf'].update({
                'cluster_name': args.cluster_name,
                'base_domain': result['cloud']['base_domain']
            })
    return result
