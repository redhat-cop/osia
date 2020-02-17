from abc import abstractmethod, ABC
from jinja2 import Environment, PackageLoader
from typing import ClassVar


class AbstractInstaller(ABC):
    __env: Environment = None

    def __init__(self,
                 cluster_name=None,
                 base_domain=None,
                 master_flavor=None,
                 master_replicas=None,
                 pull_secret_file=None,
                 ssh_key_file=None,
                 worker_flavor=None,
                 worker_replicas=None,
                 certificate_bundle_file=None,
                 cluster_directory=None):
        self.cluster_name = cluster_name
        self.base_domain = base_domain
        self.master_flavor = master_flavor
        self.master_replicas = master_replicas
        self.pull_secret_file = pull_secret_file
        self.pull_secret = None
        self.ssh_key_file = ssh_key_file
        self.ssh_key = None
        self.certificate_bundle_file = certificate_bundle_file
        self.certificate_bundle = None
        self.worker_flavor = worker_flavor
        self.worker_replicas = worker_replicas
        self.cluster_directory = cluster_directory

    @abstractmethod
    def acquire_resources(self):
        pass

    @abstractmethod
    def get_template_name(self):
        pass

    @abstractmethod
    def post_installation(self):
        pass

    def process_template(self):
        with open(self.pull_secret_file) as ps:
            self.pull_secret = ps.read()
        with open(self.ssh_key_file) as key_file:
            self.ssh_key = key_file.read()
        if self.certificate_bundle_file is not None:
            with open(self.certificate_bundle_file) as cert_file:
                self.certificate_bundle = cert_file.read()
        template = AbstractInstaller.get_environment().get_template(self.get_template_name())
        result = template.render(self.__dict__)
        with open(f"{self.cluster_name}/install-config.yaml", "w") as yaml_file:
            yaml_file.write(result)

    @classmethod
    def get_environment(cls) -> Environment:
        if cls.__env is None:
            cls.__env = Environment(loader=PackageLoader("osia.installer"))
        return cls.__env


class InstallerProvider(object):
    __instance: "InstallerProvider" = None

    @classmethod
    def instance(cls) -> "InstallerProvider":
        if cls.__instance is None:
            cls.__instance = cls()
        return cls.__instance

    @classmethod
    def register(cls, name, instance):
        cls.instance().add_installer(name, instance)

    def __init__(self):
        self.installers = {}

    def add_installer(self, name: str, instance: ClassVar):
        self.installers[name] = instance

    def __getitem__(self, name: str) -> ClassVar:
        return self.installers[name]
