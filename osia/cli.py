"""Module implements command line interface for the installation of
openshift"""
import argparse
import logging
from typing import List
import coloredlogs

from dynaconf import settings
from .installer import install_cluster, delete_cluster, storage, download_installer


def _identity(in_attr: str) -> str:
    return in_attr


def _read_list(in_str: str) -> List[str]:
    return in_str.split(',')


ARGUMENTS = {
    'common': {
        'cloud': {'help': 'Cloud provider to be used.', 'type': str,
                  'choices': ['openstack', 'aws']},
        'dns_provider': {'help': 'Provider of dns used with openstack cloud',
                         'type': str, 'choices': ['nsupdate', 'route53']},
        'os_image': {'help': 'Image to override'}
    },
    'install': {
        'base_domain': {'help': 'Base domain for the cluster', 'type': str},
        'master_flavor': {'help': 'Flavor used for master nodes'},
        'master_replicas': {'help': 'Number of replicas for master nodes', 'type': int},
        'pull_secret_file': {'help': 'File containing pull secret from `cloud.redhat.com`'},
        'ssh_key_file': {'help': 'File with ssh key used by installer'},
        'list_of_regions': {'help': 'List of regions, comma separated values', 'proc': _read_list},
        'osp_cloud': {'help': 'Name of openstack cloud identity in clouds.yaml'},
        'osp_base_flavor': {'help': 'Base flavor to be used in openstack'},
        'network_list': {'help': 'List of usable openstack networks, comma separated values',
                         'proc': _read_list},
        'worker_flavor': {'help': 'flavor of worker node'},
        'worker_replicas': {'help': 'Number of replicas of worker nodes', 'type': int},
        'certificate_bundle_file': {'help': 'CA bundle file'},
        'images_dir': {'help': 'Directory where images should be stored', 'type': str,
                       'default': 'images'},
        'skip_clean': {'help': 'Skip clean when installation fails', 'action': 'store_true'},
    },
    'dns': {
        'dns_ttl': {'help': 'TTL of the records', 'type': int},
        'dns_key_file': {'help': 'Keyfile used to access dns server via nsupdate'},
        'dns_zone': {'help': 'Zone on server where the record will be stored'},
        'dns_server': {'help': 'Address of server with running bind'}
    }
}

for a in [v for a in ARGUMENTS for u, v in ARGUMENTS[a].items()]:
    if not a.get('proc', None):
        a['proc'] = _identity


def _resolve_installer(from_args):
    if from_args.installer is None and from_args.installer_version is None:
        raise Exception('Either installer or installer-version must be passed')
    if from_args.installer:
        return from_args.installer

    return download_installer(from_args.installer_version,
                              from_args.installers_dir,
                              from_args.installer_source)


def _merge_dictionaries(from_args):
    result = {'cloud': None,
              'dns': None,
              'installer': _resolve_installer(from_args),
              'cloud_name': None,
              'cluster_name': from_args.cluster_name,
              'os_image': None}
    if not from_args.__contains__('cloud'):
        return result
    defaults = settings.as_dict()
    if from_args.dns_provider is not None:
        result['dns'] = {'provider': from_args.dns_provider,
                         'conf': defaults['DNS'][from_args.dns_provider]}
        result['dns']['conf'].update(
            {j[4:]: i['proc'](vars(from_args)[j])
             for j, i in ARGUMENTS['dns'].items()
             if vars(from_args)[j] is not None}
        )
    if from_args.cloud is not None:
        result['os_image'] = from_args.os_image
        result['cloud_name'] = from_args.cloud
        result['cloud'] = defaults['CLOUD'][from_args.cloud]
        result['cloud'].update(
            {j: i['proc'](vars(from_args)[j]) for j, i in ARGUMENTS['install'].items()
             if vars(from_args)[j] is not None}
        )
        if result['dns'] is not None:
            result['dns']['conf'].update({
                'cluster_name': from_args.cluster_name,
                'base_domain': result['cloud']['base_domain']
            })
    return result


def _exec_install_cluster(args):
    conf = _merge_dictionaries(args)
    if not args.skip_git:
        storage.check_repository()
    logging.info('Starting the installer with cloud name %s', conf['cloud_name'])
    install_cluster(
        conf['cloud_name'],
        conf['cluster_name'],
        conf['cloud'],
        conf['installer'],
        os_image=conf['os_image'],
        dns_settings=conf['dns']
    )
    if not args.skip_git:
        storage.write_changes(conf['cluster_name'])


def _exec_delete_cluster(args):
    conf = _merge_dictionaries(args)

    if not args.skip_git:
        storage.check_repository()

    delete_cluster(conf['cluster_name'], conf['installer'])

    if not args.skip_git:
        storage.delete_directory(conf['cluster_name'])


def _get_helper(parser: argparse.ArgumentParser):
    def printer(unused_conf):
        print("Operation not set, please specify either install or clean!")
        parser.print_help()
    return printer


def _create_commons():
    commons = argparse.ArgumentParser(add_help=False)
    common_arguments = [
        [['--cluster-name'], dict(required=True, help='Name of the cluster')],
        [['--installer'], dict(required=False,
                               help='Executable binary of openshift install cli', default=None)],
        [['--installer-version'], dict(help='Version of downloader to be downloaded',
                                       default='latest', type=str)],
        [['--installer-source'], dict(type=str,
                                      help='Set the source to search for installer',
                                      choices=["prod", "devel", "prev"],
                                      default='prod')],
        [['--installers-dir'], dict(help='Folder where installers are stored',
                                    required=False, default='installers')],
        [['--skip-git'], dict(help='When set, the persistance will be skipped',
                              action='store_true')],
        [['-v', '--verbose'], dict(help='Increase verbosity level', action='store_true')]
    ]
    for k in common_arguments:
        commons.add_argument(*k[0], **k[1])
    return commons


def _setup_parser():
    commons = _create_commons()

    parser = argparse.ArgumentParser("osia")
    parser.set_defaults(func=_get_helper(parser))
    sub_parsers = parser.add_subparsers()

    install = sub_parsers.add_parser('install', help='Install new cluster', parents=[commons])

    for arg, value in {k: v for a in ARGUMENTS for k, v in ARGUMENTS[a].items()}.items():
        install.add_argument(f"--{arg.replace('_', '-')}",
                             help=value.get('help', None),
                             type=value.get('type', None))

    install.set_defaults(func=_exec_install_cluster)

    clean = sub_parsers.add_parser('clean', help='Remove cluster', parents=[commons])
    clean.set_defaults(func=_exec_delete_cluster)
    return parser


def main_cli():
    """Function represents main entrypoint for the
    osia intaller

    It sets up the cli and starts the executor."""
    parser = _setup_parser()
    args = parser.parse_args()
    if vars(args).get('verbose', False):
        coloredlogs.install(level='DEBUG')
    else:
        coloredlogs.install(level='INFO')

    args.func(args)
