"""
Module implements merging of default configuration obtained via Dynaconf
with command line arguments.
"""
import argparse
import logging
import warnings
from typing import Dict, Optional

from dynaconf import Dynaconf

settings = Dynaconf(
    environments=True,
    lowercase_read=False,
    load_dotenv=True,
    settings_files=[name + end for name in ["settings", ".secrets"] for end in [".yaml", ".yml"]]
)


def _resolve_cloud_name(args: argparse.Namespace) -> Optional[Dict]:
    defaults = settings.as_dict()

    if defaults['CLOUD'][args.cloud].get('environments', None) is None:
        warnings.warn('[DEPRECATION WARNING] The structure of settings.yaml is changed, '
                      'please use environments list and default_env option. This behavior will be '
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
    logging.debug("No environment found, maybe all variables are passed from command line")
    return None


def read_config(args: argparse.Namespace, default_args: Dict) -> Dict:
    """
    Reads config from Dynaconf and merges it with arguments provided via commandline.
    """
    result = {'cloud': None,
              'dns': None,
              'cloud_name': None,
              'cluster_name': args.cluster_name}
    if not args.__contains__('cloud'):
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
    if args.cloud is not None:
        cloud_defaults = _resolve_cloud_name(args)
        result['cloud_name'] = args.cloud
        result['cloud'] = cloud_defaults
        result['cloud'].update(
            {j: i['proc'](vars(args)[j]) for j, i in default_args['install'].items()
             if vars(args)[j] is not None}
        )

        if result['dns'] is not None:
            result['dns']['conf'].update({
                'cluster_name': args.cluster_name,
                'base_domain': result['cloud']['base_domain']
            })
    return result
