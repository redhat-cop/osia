# -*- coding: utf-8 -*-
#
# Copyright 2022 Osia authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Module implements command line interface for the installation of
openshift"""
import argparse
import logging
from typing import List
import coloredlogs

from .installer import install_cluster, delete_cluster, storage, download_installer
from .config import read_config


def _identity(in_attr: str) -> str:
    return in_attr


def _read_list(in_str: str) -> List[str]:
    return in_str.split(',')


ARGUMENTS = {
    'common': {
        'cloud': {'help': 'Cloud provider to be used.', 'type': str,
                  'choices': ['openstack', 'aws']},
        'cloud_env': {'help': 'Environment of cloud to be used.', 'type': str},
        'dns_provider': {'help': 'Provider of dns used with openstack cloud',
                         'type': str, 'choices': ['nsupdate', 'route53']}
    },
    'install': {
        'os_image': {'help': 'Image to override', 'type': str},
        'base_domain': {'help': 'Base domain for the cluster', 'type': str},
        'master_flavor': {'help': 'Flavor used for master nodes'},
        'master_replicas': {'help': 'Number of replicas for master nodes', 'type': int},
        'pull_secret_file': {'help': 'File containing pull secret from `cloud.redhat.com`'},
        'ssh_key_file': {'help': 'File with ssh key used by installer'},
        'list_of_regions': {'help': 'List of regions, comma separated values', 'proc': _read_list},
        'osp_cloud': {'help': 'Name of openstack cloud identity in clouds.yaml'},
        'osp_base_flavor': {'help': 'Base flavor to be used in openstack'},
        'osp_image_download': {'help': 'Enable image download by osia instead of openshift-install',
                               'action': 'store_true'},
        'osp_image_unique': {'help': 'Upload unique image per cluster',
                             'action': 'store_true'},
        'network_list': {'help': 'List of usable openstack networks, comma separated values',
                         'proc': _read_list},
        'worker_flavor': {'help': 'flavor of worker node'},
        'worker_replicas': {'help': 'Number of replicas of worker nodes', 'type': int},
        'certificate_bundle_file': {'help': 'CA bundle file'},
        'images_dir': {'help': 'Directory where images should be stored', 'type': str,
                       'default': 'images'},
        'skip_clean': {'help': 'Skip clean when installation fails', 'action': 'store_true'},
        'enable_fips': {'help': 'Enable fips mode to the cluster', 'action': 'store_true'},
        'enable_ipv6': {'help': 'Install custer with internally used ipv6.',
                        'action': 'store_true'},
    },
    'deprecated': {
        'psi_cloud': {'help': 'DEPRECATED see osp_cloud'},
        'psi_base_flavor': {'help': 'DEPRECATED see osp_base_flavor'},
    },
    'dns': {
        'dns_ttl': {'help': 'TTL of the records', 'type': int},
        'dns_key_file': {'help': 'Keyfile used to access dns server via nsupdate'},
        'dns_zone': {'help': 'Zone on server where the record will be stored'},
        'dns_server': {'help': 'Address of server with running bind'},
        'dns_use_ipv4': {'help': 'Use only IPv4 for DNS settings', 'action': 'store_const',
                         'const': True}
    }
}

for a in [v for _, x in ARGUMENTS.items() for u, v in x.items()]:
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
    result = read_config(from_args, ARGUMENTS)
    result["installer"] = _resolve_installer(from_args)
    if result.get('cloud'):
        # pylint: disable=unsupported-assignment-operation
        result['cloud']['installer'] = result['installer']
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

    for arg, value in sorted({k: v for _, x in ARGUMENTS.items() for k, v in x.items()}.items()):
        install.add_argument(f"--{arg.replace('_', '-')}",
                             **{k: v for k, v in value.items() if k != 'proc'})
    install.set_defaults(func=_exec_install_cluster)

    clean = sub_parsers.add_parser('clean', help='Remove cluster', parents=[commons])
    clean.set_defaults(func=_exec_delete_cluster)
    return parser


def main_cli():
    """Function represents main entrypoint for the
    osia installer

    It sets up the cli and starts the executor."""
    parser = _setup_parser()
    args = parser.parse_args()
    if vars(args).get('verbose', False):
        coloredlogs.install(level='DEBUG')
    else:
        coloredlogs.install(level='INFO')
    logging.captureWarnings(True)

    args.func(args)
