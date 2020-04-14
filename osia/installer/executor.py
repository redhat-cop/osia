# -*- coding: utf-8 -*-
#
# Copyright 2020 Osia authors
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
"""Executor module implements controlling logic of cluster installation"""
from os import environ
from subprocess import Popen
from pathlib import Path
import logging

from .clouds import InstallerProvider
from .clouds.openstack import delete_fips
from .dns import DNSProvider


class InstallerExecutionException(Exception):
    """Class represents exception raised by installer failure"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


def execute_installer(installer, base_path, operation, os_image=None):
    """Function executes actual installation of OpenShift"""
    additional_env = None
    if os_image is not None and os_image:
        additional_env = environ.copy()
        additional_env.update({'OPENSHIFT_INSTALL_OS_IMAGE_OVERRIDE': os_image})
    with Popen([installer, operation, 'cluster', '--dir', base_path],
               env=additional_env, universal_newlines=True) as proc:
        proc.wait()
        if proc.returncode != 0:
            raise InstallerExecutionException("Failed execution of installer")


def install_cluster(cloud_provider,
                    cluster_name, configuration,
                    installer,
                    os_image=None,
                    dns_settings=None):
    """Function represents main entrypoint to all logic necessary for
    cluster's deployment."""
    # pylint: disable=too-many-arguments
    cluster_path = Path("./") / cluster_name
    if cluster_path.exists():
        logging.error("Path %s already exists, remove it before continuing",
                      cluster_path.as_posix())
        return
    cluster_path.mkdir()
    inst = InstallerProvider.instance()[cloud_provider](cluster_name=cluster_name, **configuration)
    inst.acquire_resources()
    dns_prov = None
    if dns_settings is not None:
        dns_prov = DNSProvider.instance()[dns_settings['provider']](**dns_settings['conf'])
        dns_prov.add_api_domain(inst.osp_fip)
        dns_prov.marshall(cluster_name)

    inst.process_template()

    try:
        execute_installer(installer, cluster_name, 'create', os_image=os_image)
    except InstallerExecutionException as exception:
        logging.error(exception)
        if inst.check_clean():
            delete_cluster(cluster_name, installer)
            return

    inst.post_installation()

    if dns_settings is not None:
        dns_prov.add_apps_domain(inst.apps_fip)
        dns_prov.marshall(cluster_name)


def delete_cluster(cluster_name, installer):
    """Function is the controller of all actions leading to the
    cluster's deletion."""
    dns_prov = DNSProvider.instance().load(cluster_name)
    if dns_prov is not None:
        dns_prov.delete_domains()
    fips_file = Path(cluster_name) / "fips.json"
    if fips_file.exists():
        delete_fips(fips_file)
        fips_file.unlink()
    for k in [1, 2]:
        try:
            logging.debug("Attempt to clean #%d", k)
            execute_installer(installer, cluster_name, 'destroy')
            break
        except InstallerExecutionException as exception:
            logging.error("Re-executing installer due to error %s", exception)
