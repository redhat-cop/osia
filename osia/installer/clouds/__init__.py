"""Module implements configuration objects for install-config creation"""
from .base import InstallerProvider
from .aws import AWSInstaller
from .openstack import OpenstackInstaller


InstallerProvider.register('aws', AWSInstaller)
InstallerProvider.register('openstack', OpenstackInstaller)
