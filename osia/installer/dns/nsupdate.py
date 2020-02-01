from osia.installer.dns.base import DNSUtil
from subprocess import Popen, PIPE


class NSUpdate(DNSUtil):
    def __init__(self, key_file=None, server=None, zone=None, **kwargs):
        super().__init__(**kwargs)
        self.key_file = key_file
        self.server = server
        self.zone = zone

    def _exec_nsupdate(self, string: str):
        nsu = Popen(["nsupdate", "-k", self.key_file], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out, err = nsu.communicate(string.encode('utf-8'))
        print(out)
        print(err)

    def provider_name(self):
        return 'nsupdate'

    def _get_start(self):
        return f"""server {self.server}
zone {self.zone}"""

    def _get_suffix(self):
        return f"{self.cluster_name}.{self.base_domain}"

    def add_api_domain(self, ip_addr: str):
        nsupdate_string = f"""{self._get_start()}
update add api.{self._get_suffix()} {self.ttl} A {ip_addr}
send
"""
        self._exec_nsupdate(nsupdate_string)

    def add_apps_domain(self, ip_addr: str):
        nsupdate_string = f"""{self._get_start()}
update add apps.{self._get_suffix()} {self.ttl} A {ip_addr}
update add \\*.apps.{self._get_suffix()} {self.ttl} A {ip_addr}
send
"""
        self._exec_nsupdate(nsupdate_string)

    def delete_domains(self):
        nsupdate_string = f"""{self._get_start()}
update delete apps.{self._get_suffix()} A
update delete \\*.apps.{self._get_suffix()} A
update delete api.{self._get_suffix()} A
send"""

        self._exec_nsupdate(nsupdate_string)
