from .base import AbstractInstaller
from operator import itemgetter
from openstack.connection import from_config, Connection
from typing import List, Optional
import json
from os import path


def load_connection_openstack(conn_name: str, args=None) -> Connection:
    connection = from_config(cloud=conn_name, options=args)
    if connection is None:
        raise Exception(f"Unable to connect to ${conn_name}")
    return connection


def update_json(json_file, fip):
    res = None
    with open(json_file) as inp:
        res = json.load(inp)

    res['fips'].append(fip)
    with open(json_file, "w") as out:
        json.dump(res, out)


def delete_fips(fips_file):
    fips = None
    with open(fips_file) as fi:
        fips = json.load(fi)
    connection = load_connection_openstack(fips['cloud'])
    os_fips = [j for k in fips['fips'] for j in connection.network.ips(floating_ip_address=k)]
    for i in os_fips:
        connection.network.delete_ip(i)


def find_best_fit(networks: dict) -> str:
    return max(networks.items(), key=itemgetter(1))[0]


def find_fit_network(osp_connection: Connection, networks: List[str]) -> Optional[str]:
    named_networks = {k['name']: k for k in osp_connection.list_networks() if k['name'] in networks}
    results = dict()
    for net_name in networks:
        net_avail = osp_connection.network.get_network_ip_availability(named_networks[net_name])
        results[net_name] = net_avail['total_ips'] / net_avail['used_ips']
    result = find_best_fit(results)
    return (named_networks[result]['id'], result)


def find_cluster_ports(osp_connection: Connection, cluster_name: str):
    port_list = [k for k in osp_connection.list_ports()
                 if k.name.startswith(cluster_name) and k.name.endswith('ingress-port')]
    port = next(iter(port_list), None)
    if port is None:
        raise Exception(f"Ingress port for cluster {cluster_name} was not found")
    return port


def attach_fip_to_port(osp_connection: Connection, fip_addr, ingress_port):
    osp_connection.network.add_ip_to_port(ingress_port, fip_addr)


def get_floating_ip(osp_connection: Connection, cloud: str, network_id: str, cluster_name: str):
    fip = osp_connection.network.create_ip(floating_network_id=network_id)
    if fip is None:
        raise Exception(f"Allocation of Ip failed for network ${network_id}")

    if path.exists(f"{cluster_name}/fips.json"):
        update_json(f"{cluster_name}/fips.json", fip.floating_ip_address)
    else:
        with open(f"{cluster_name}/fips.json", "w") as fips:
            d = {'cloud': cloud, 'fips': [fip.floating_ip_address]}
            json.dump(d, fips)
    return fip


class OpenstackInstaller(AbstractInstaller):
    def __init__(self,
                 osp_cloud=None,
                 osp_base_flavor=None,
                 network_list=None,
                 args=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.osp_cloud = osp_cloud
        self.osp_base_flavor = osp_base_flavor
        self.network_list = network_list
        self.args = args
        self.osp_FIP = None
        self.network = None
        self.connection = None
        self.apps_fip = None
        self.osp_network = None

    def get_template_name(self):
        return 'openstack.jinja2'

    def acquire_resources(self):
        self.connection = load_connection_openstack(self.osp_cloud)
        self.network, self.osp_network = find_fit_network(self.connection, self.network_list)
        if self.network is None:
            raise Exception("No suitable network found")
        self.osp_FIP = get_floating_ip(self.connection,
                                       self.osp_cloud,
                                       self.network,
                                       self.cluster_name).floating_ip_address

    def post_installation(self):
        ingress_port = find_cluster_ports(self.connection, self.cluster_name)
        self.apps_fip = get_floating_ip(self.connection,
                                        self.osp_cloud,
                                        self.network,
                                        self.cluster_name)
        attach_fip_to_port(self.connection, self.apps_fip, ingress_port)
        self.apps_fip = apps_fip.floating_ip_address
