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
"""Module implements support for Openstack installation"""
from operator import itemgetter
from pathlib import Path
from typing import List, Optional, Tuple
from os import path

import json
import warnings
import logging

from munch import Munch
from openstack.connection import from_config, Connection
from openstack.network.v2.floating_ip import FloatingIP
from openstack.image.v2.image import Image
from openstack.exceptions import SDKException
from osia.installer.clouds.base import AbstractInstaller
from osia.installer.downloader import get_url, download_image


class ImageException(Exception):
    """
    Image exception encapsulates Exception happening while image resolution
    """
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)


def _load_connection_openstack(conn_name: str, args=None) -> Connection:
    connection = from_config(cloud=conn_name, options=args)
    if connection is None:
        raise Exception(f"Unable to connect to ${conn_name}")
    return connection


def _update_json(json_file: str, fip: str):
    res = None
    with open(json_file) as inp:
        res = json.load(inp)

    res['fips'].append(fip)
    with open(json_file, "w") as out:
        json.dump(res, out)


def delete_fips(fips_file: str):
    """Deletes floating ips stored in configuration file"""
    fips = None
    with open(fips_file) as fi_file:
        fips = json.load(fi_file)
    connection = _load_connection_openstack(fips['cloud'])
    os_fips = [j for k in fips['fips'] for j in connection.network.ips(floating_ip_address=k)]
    for i in os_fips:
        connection.network.delete_ip(i)


def delete_image(fips_file, cluster_name):
    """Function checkes the uploaded image into openstack
    and removes from its metadata information about associated
    cluster.
    If last associated cluster was removed, the image is deleted"""
    fips = None
    with open(fips_file) as json_file:
        fips = json.load(json_file)
    if fips.get('image', None) is None:
        return
    connection = _load_connection_openstack(fips['cloud'])
    image = connection.image.find_image(fips['image'])
    clusters = image.properties['osia_clusters'].split(',')
    clusters.remove(cluster_name)
    if len(clusters) == 0:
        logging.info("Deleting uploaded image %s, since all clusters were removed", image.name)
        connection.image.delete_image(image)
    else:
        logging.info("Removing cluster %s from image %s metadata", cluster_name, image.name)
        connection.image.update_image(image, osia_clusters=','.join(clusters))


def _find_best_fit(networks: dict) -> str:
    return max(networks.items(), key=itemgetter(1))[0]


def _find_fit_network(osp_connection: Connection,
                      networks: List[str]) -> Tuple[Optional[str], Optional[str]]:
    named_networks = {k['name']: k for k in osp_connection.list_networks() if k['name'] in networks}
    results = dict()
    for net_name in networks:
        net_avail = osp_connection.network.get_network_ip_availability(named_networks[net_name])
        results[net_name] = net_avail['total_ips'] / net_avail['used_ips']
    result = _find_best_fit(results)
    return named_networks[result]['id'], result


def _find_cluster_ports(osp_connection: Connection, cluster_name: str) -> Munch:
    port_list = [k for k in osp_connection.list_ports()
                 if k.name.startswith(cluster_name) and k.name.endswith('ingress-port')]
    port = next(iter(port_list), None)
    if port is None:
        raise Exception(f"Ingress port for cluster {cluster_name} was not found")
    return port


def _attach_fip_to_port(osp_connection: Connection, fip_addr, ingress_port):
    osp_connection.network.add_ip_to_port(ingress_port, fip_addr)


def _get_floating_ip(osp_connection: Connection,
                     cloud: str,
                     network_id: str,
                     cluster_name: str,
                     purpose: str) -> FloatingIP:
    fip = osp_connection.network.create_ip(floating_network_id=network_id,
                                           description=f"{cluster_name}-{purpose}")
    if fip is None:
        raise Exception(f"Allocation of Ip failed for network ${network_id}")

    if path.exists(f"{cluster_name}/fips.json"):
        _update_json(f"{cluster_name}/fips.json", fip.floating_ip_address)
    else:
        with open(f"{cluster_name}/fips.json", "w") as fips:
            conf = {'cloud': cloud, 'fips': [fip.floating_ip_address]}
            json.dump(conf, fips)
    return fip


def add_cluster(osp_connection: Connection, image: Image, cluster_name: str):
    """Function adds cluster name to image metadata in order to prevent
    image deletion"""
    clusters = image.properties['osia_clusters'].split(',')
    clusters.append(cluster_name)
    osp_connection.image.update_image(image, osia_clusters=','.join(clusters))


# pylint: disable=too-many-arguments
def resolve_image(osp_connection: Connection,
                  cloud: str,
                  cluster_name: str,
                  images_dir: str,
                  installer: str,
                  error: Optional[Exception]):
    """Function searches for image in openstack and creates it
    if it doesn't exist"""
    inst_url, version = get_url(installer)
    image_name = f"osia-rhcos-{version}"
    image = osp_connection.image.find_image(image_name, ignore_missing=True)
    if image is None:
        image_path = Path(images_dir).joinpath(f"rhcos-{version}.qcow2")
        image_file = None
        if image_path.exists():
            logging.info("Found image at %s", image_path.name)
            image_file = image_path.as_posix()
        else:
            logging.info("Starting download of image %s", inst_url)
            image_file = download_image(inst_url, image_path.as_posix())

        logging.info("Starting upload of image into openstack")
        osp_connection.create_image(image_name, filename=image_file,
                                    container_format="bare", disk_format="qcow2", wait=True,
                                    osia_clusters=cluster_name, visibility='private')
        logging.info("Upload finished")
        image = osp_connection.image.find_image(image_name)
        logging.info("Image uploaded as %s", image.name)
    else:
        logging.info("Reusing found image in openstack %s", image.name)
        try:
            add_cluster(osp_connection, image, cluster_name)
        except SDKException as err:
            if error is not None:
                raise ImageException("Couldn't add cluster to image") from err
            logging.warning("Image disappeared while metadata were written, trying again")
            logging.debug("Openstack error: %s", err)
            return resolve_image(osp_connection, cloud, cluster_name, images_dir, installer, err)
    with open(Path(cluster_name).joinpath("fips.json"), "w") as fips:
        obj = {'cloud': cloud, 'fips': list(), 'image': image_name}
        json.dump(obj, fips)
    return image.name


class OpenstackInstaller(AbstractInstaller):
    """Class containing configuration related to openstack"""
    # pylint: disable=too-many-instance-attributes,too-many-arguments
    def __init__(self,
                 osp_cloud=None,
                 osp_base_flavor=None,
                 network_list=None,
                 os_image=None,
                 images_dir=None,
                 osp_image_download=False,
                 args=None,
                 **kwargs):
        super().__init__(**kwargs)
        if 'psi_base_flavor' in kwargs:
            warnings.warn("[Deprecation warning]: option psi_base_flavor was replaced by option "
                          "osp_base_flavor this option will be removed in next releases.")
            self.osp_base_flavor = kwargs['psi_base_flavor']
        if 'psi_cloud' in kwargs:
            warnings.warn("[Deprecation warning]: option psi_cloud was replaced by option osp_cloud"
                          "this option will be removed in next releases.")
            self.osp_cloud = kwargs['psi_cloud']

        if osp_cloud is not None:
            self.osp_cloud = osp_cloud
        if osp_base_flavor is not None:
            self.osp_base_flavor = osp_base_flavor
        self.network_list = network_list
        self.args = args
        self.os_image = os_image
        self.image_download = osp_image_download
        self.osp_fip = None
        self.network = None
        self.connection = None
        self.apps_fip = None
        self.osp_network = None
        self.images_dir = images_dir

    def get_template_name(self):
        return 'openstack.jinja2'

    def acquire_resources(self):
        self.connection = _load_connection_openstack(self.osp_cloud)
        if self.image_download and (self.os_image is None or self.os_image == ""):
            self.os_image = resolve_image(self.connection, self.osp_cloud, self.cluster_name,
                                          self.images_dir, self.installer, None)
        self.network, self.osp_network = _find_fit_network(self.connection, self.network_list)
        if self.network is None:
            raise Exception("No suitable network found")
        self.osp_fip = _get_floating_ip(self.connection,
                                        self.osp_cloud,
                                        self.network,
                                        self.cluster_name,
                                        "api").floating_ip_address

    def post_installation(self):
        ingress_port = _find_cluster_ports(self.connection, self.cluster_name)
        apps_fip = _get_floating_ip(self.connection,
                                    self.osp_cloud,
                                    self.network,
                                    self.cluster_name,
                                    "ingress")
        _attach_fip_to_port(self.connection, apps_fip, ingress_port)
        self.apps_fip = apps_fip.floating_ip_address
