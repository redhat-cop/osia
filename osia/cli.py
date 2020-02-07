import argparse
import logging, coloredlogs
from typing import List, Callable, Union, Any

from dynaconf import settings
from osia.installer import install_cluster, delete_cluster, storage, download_installer


def identity(in_attr: str) -> str:
    return in_attr


def read_list(in_str: str) -> List[str]:
    return in_str.split(',')


arguments = {
    'common': {
        'cloud': {'help': 'Cloud provider to be used, one of (openstack, aws)', 'type': str},
        'dns_provider': {'help': 'Provider of dns used with openstack cloud', 'type': str},
        'os_image': {'help': 'Image to override'}
    },
    'install': {
        'base_domain': {'help': 'Base domain for the cluster', 'type': str},
        'master_flavor': {'help': 'Flavor used for master nodes'},
        'pull_secret_file': {'help': 'File containing pull secret from `cloud.redhat.com`'},
        'ssh_key_file': {'help': 'File with ssh key used by installer'},
        'list_of_regions': {'help': 'List of regions, comma separated values', 'proc': read_list},
        'osp_cloud': {'help': 'Name of openstack cloud identity in clouds.yaml'},
        'osp_base_flavor': {'help': 'Base flavor to be used in openstack'},
        'network_list': {'help': 'List of usable openstack networks, comma separated values',
                         'proc': read_list},
        'worker_flavor': {'help': 'flavor of worker node'},
        'certificate_bundle_file': {'help': 'CA bundle file'},
    },
    'dns': {
        'dns_ttl': {'help': 'TTL of the records', 'type': int},
        'dns_key_file': {'help': 'Keyfile used to access dns server via nsupdate'},
        'dns_zone': {'help': 'Zone on server where the record will be stored'},
        'dns_server': {'help': 'Address of server with running bind'}
    }
}

for a in [v for a in arguments for u, v in arguments[a].items()]:
    if not a.get('proc', None):
        a['proc'] = identity

def resolve_installer(from_args):
    if from_args.installer is None and from_args.installer_version is None:
        raise Exception('Either installer or installer-version must be passed')
    if from_args.installer:
        return from_args.installer

    return download_installer(from_args.installer_version,
                              from_args.installers_dir,
                              from_args.installer_devel)


def merge_dictionaries(from_args):
    result = {'cloud': None,
              'dns': None,
              'installer': resolve_installer(from_args),
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
             for j, i in arguments['dns'].items()
             if vars(from_args)[j] is not None}
        )
    if from_args.cloud is not None:
        result['os_image'] = from_args.os_image
        result['cloud_name'] = from_args.cloud
        result['cloud'] = defaults['CLOUD'][from_args.cloud]
        result['cloud'].update(
            {j: i['proc'](vars(from_args)[j]) for j, i in arguments['install'].items()
             if vars(from_args)[j] is not None}
        )
        if result['dns'] is not None:
            result['dns']['conf'].update({
                'cluster_name': from_args.cluster_name,
                'base_domain': result['cloud']['base_domain']
            })
    return result


def exec_install_cluster(args):
    conf = merge_dictionaries(args)
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


def exec_delete_cluster(args):
    conf = merge_dictionaries(args)

    if not args.skip_git:
        storage.check_repository()

    delete_cluster(conf['cluster_name'], conf['installer'])

    if not args.skip_git:
        storage.delete_directory(conf['cluster_name'])


def get_helper(parser: argparse.ArgumentParser):
    def printer(conf):
        print("Operation set, please specify either install or clean!")
        parser.print_help()
    return printer


def setup_parser():
    commons = argparse.ArgumentParser(add_help=False)
    commons.add_argument('--cluster-name', required=True, help='Name of the cluster')
    commons.add_argument('--installer',
                         required=False,
                         help='Executable binary of openshift install cli', default=None)
    commons.add_argument('--installer-version', help='Version of downloader to be downloaded', default='latest', type=str)
    commons.add_argument('--installer-devel', action='store_true',
                         help='If set installer will be searched at devel repository')
    commons.add_argument('--installers-dir', help='Folder where installers are stored', required=False, default='installers' )
    commons.add_argument('--skip-git',
                         help='When set, the persistance will be skipped', action='store_true')

    parser = argparse.ArgumentParser("osia")
    parser.set_defaults(func=get_helper(parser))
    sub_parsers = parser.add_subparsers()

    install = sub_parsers.add_parser('install', help='Install new cluster', parents=[commons])

    for arg, value in {k: v for a in arguments for k, v in arguments[a].items()}.items():
        install.add_argument(f"--{arg.replace('_', '-')}",
                             help=value.get('help', None),
                             type=value.get('type', None))

    install.set_defaults(func=exec_install_cluster)

    clean = sub_parsers.add_parser('clean', help='Remove cluster', parents=[commons])
    clean.set_defaults(func=exec_delete_cluster)
    return parser


def main_cli():
    coloredlogs.install(level='INFO')
    parser = setup_parser()
    args = parser.parse_args()
    args.func(args)


