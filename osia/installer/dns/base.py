from abc import ABC, abstractmethod
from typing import ClassVar, Optional
from os import path
from pathlib import Path
import json


class DNSProvider:
    __instance = None

    @classmethod
    def register_provider(cls, name: str, clazz: ClassVar):
        cls.instance()._add_provider(name, clazz)

    @classmethod
    def instance(cls):
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    def __init__(self):
        self.providers = dict()

    def _add_provider(self, name: str, clazz: ClassVar):
        self.providers[name] = clazz

    def __getitem__(self, name: str) -> ClassVar:
        return self.providers[name]

    def load(self, directory: str) -> Optional['DNSUtil']:
        for k in self.providers:
            if path.exists(f"{directory}/{k}.json"):
                res = self[k]()
                res.unmarshall(directory)
                return res
        return None


class DNSUtil(ABC):

    def __init__(self,
                 cluster_name=None,
                 base_domain=None,
                 ttl=None):
        self.cluster_name = cluster_name
        self.base_domain = base_domain
        self.ttl = ttl

    @abstractmethod
    def add_api_domain(self, ip_addr: str):
        pass

    @abstractmethod
    def add_apps_domain(self, ip_addr: str):
        pass

    @abstractmethod
    def delete_domains(self):
        pass

    @abstractmethod
    def provider_name(self):
        pass

    def marshall(self, out_dir: str):
        with open(f"{out_dir}/{self.provider_name()}.json", "w") as output:
            json.dump(self, output, default=lambda o: o.__dict__)

    def unmarshall(self, in_dir: str):
        with open(f"{in_dir}/{self.provider_name()}.json") as in_stream:
            d = json.load(in_stream)
            for k in d:
                setattr(self, k, d[k])

    def delete_file(self):
        p = Path(self.cluster_name) / f"{self.provider_name()}.json"
        if p.exists():
            p.unlink()
