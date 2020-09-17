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
"""Module implements methods specific for nsupate provider"""
import logging
from subprocess import Popen, PIPE
from osia.installer.dns.base import DNSUtil
from osia.installer.clouds.base import AbstractInstaller


class NSUpdate(DNSUtil):
    """Implementation of DNSUtil specific for nsupdate dns provider"""
    def __init__(self, key_file=None, server=None, zone=None, **kwargs):
        super().__init__(**kwargs)
        self.key_file = key_file
        self.server = server
        self.zone = zone

    def _exec_nsupdate(self, string: str):
        with Popen(["nsupdate", "-k", self.key_file], stdin=PIPE, universal_newlines=True) as nsu:
            nsu.communicate(string)
            self.modified = True

    def provider_name(self):
        return 'nsupdate'

    def _get_start(self):
        result = str()
        if self.server:
            result += f"server {self.server}\n"
        if self.zone:
            result += f"zone {self.zone}\n"
        return result

    def _get_suffix(self):
        return f"{self.cluster_name}.{self.base_domain}"

    def add_api_domain(self, instance: AbstractInstaller):
        if instance.get_api_ip() is None:
            logging.debug("Not applying dns settings since no ip address is associated")
            return
        logging.info("Adding api domain api.%s for floating ip addr %s",
                     self._get_suffix(), instance.get_api_ip())
        nsupdate_string = f"""{self._get_start()}
update add api.{self._get_suffix()} {self.ttl} A {instance.get_api_ip()}
send
"""
        self._exec_nsupdate(nsupdate_string)

    def add_apps_domain(self, instance: AbstractInstaller):
        if instance.get_apps_ip() is None:
            logging.debug("Not applying dns settings since no ip address is associated")
            return
        logging.info("Adding apps domain *.apps.%s for floating ip addr %s",
                     self._get_suffix(), instance.get_apps_ip())
        nsupdate_string = f"""{self._get_start()}
update add apps.{self._get_suffix()} {self.ttl} A {instance.get_apps_ip()}
update add \\*.apps.{self._get_suffix()} {self.ttl} A {instance.get_apps_ip()}
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
        self.delete_file()
