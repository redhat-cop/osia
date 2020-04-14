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
"""Module contains basics and common functionality to set up DNS."""
from abc import ABC, abstractmethod
from typing import ClassVar, Optional
from os import path
from pathlib import Path
import json


class DNSProvider:
    """Class implements dynamic provier of DNSUtil base class"""
    __instance = None

    # pylint: disable=protected-access
    @classmethod
    def register_provider(cls, name: str, clazz: ClassVar):
        """Method to dynamically register new implementation of
        DNSUtil"""
        cls.instance().__add_provider(name, clazz)

    @classmethod
    def instance(cls) -> "DNSProvider":
        """Returns singleton instance"""
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.providers = dict()

    def __add_provider(self, name: str, clazz: ClassVar):
        self.providers[name] = clazz

    def __getitem__(self, name: str) -> ClassVar:
        return self.providers[name]

    def load(self, directory: str) -> Optional['DNSUtil']:
        """Method loads saved configuration of specific DNSUtil from
        file"""
        for k in self.providers:
            if path.exists(f"{directory}/{k}.json"):
                res = self[k]()
                res.unmarshall(directory)
                return res
        return None


class DNSUtil(ABC):
    """Class implements basic settings for """
    def __init__(self,
                 cluster_name=None,
                 base_domain=None,
                 ttl=None):
        self.cluster_name = cluster_name
        self.base_domain = base_domain
        self.ttl = ttl

    @abstractmethod
    def add_api_domain(self, ip_addr: str):
        """Method registers api domain in selected provider"""

    @abstractmethod
    def add_apps_domain(self, ip_addr: str):
        """Method registers apps domain in selected provider"""

    @abstractmethod
    def delete_domains(self):
        """Method deletes all registered domains in provider"""

    @abstractmethod
    def provider_name(self):
        """Get name of provider"""

    def marshall(self, out_dir: str):
        """Method stores current configuration on DNS provider to $provider_name.json"""
        with open(f"{out_dir}/{self.provider_name()}.json", "w") as output:
            json.dump(self, output, default=lambda o: o.__dict__)

    def unmarshall(self, in_dir: str):
        """Method loads stored configuration of DNS into provider object"""
        with open(f"{in_dir}/{self.provider_name()}.json") as in_stream:
            dns_conf = json.load(in_stream)
            for k in dns_conf:
                setattr(self, k, dns_conf[k])

    def delete_file(self):
        """Method removes unneeded configuration file"""
        file_path = Path(self.cluster_name) / f"{self.provider_name()}.json"
        if file_path.exists():
            file_path.unlink()
