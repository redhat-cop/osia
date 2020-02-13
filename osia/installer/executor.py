from os import mkdir, path, environ
from subprocess import Popen
import logging

from .clouds import InstallerProvider
from .clouds.openstack import delete_fips
from .dns import DNSProvider


class InstallerExecutionException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


def execute_installer(installer, base_path, operation, os_image=None):
    additional_env = None
    if os_image is not None:
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
    mkdir("./" + cluster_name)
    inst = InstallerProvider.instance()[cloud_provider](cluster_name=cluster_name, **configuration)
    inst.acquire_resources()
    dns_prov = None
    if dns_settings is not None:
        dns_prov = DNSProvider.instance()[dns_settings['provider']](**dns_settings['conf'])
        dns_prov.add_api_domain(inst.osp_FIP)
        dns_prov.marshall(cluster_name)

    inst.process_template()

    try:
        execute_installer(installer, cluster_name, 'create', os_image=os_image)
    except InstallerExecutionException as e:
        logging.error(e)
        delete_cluster(cluster_name, installer)

    inst.post_installation()

    if dns_settings is not None:
        dns_prov.add_apps_domain(inst.apps_fip)
        dns_prov.marshall(cluster_name)


def delete_cluster(cluster_name, installer):
    dns_prov = DNSProvider.instance().load(cluster_name)
    if dns_prov is not None:
        dns_prov.delete_domains()
    fips_file = f"{cluster_name}/fips.json"
    if path.exists(fips_file):
        delete_fips(fips_file)
    try:
        execute_installer(installer, cluster_name, 'destroy')
    except:
        execute_installer(installer, cluster_name, 'destroy')
