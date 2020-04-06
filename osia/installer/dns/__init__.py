"""Module exposes configuration to setup DNS needed for Openshift to work"""
from osia.installer.dns.nsupdate import NSUpdate
from osia.installer.dns.route53 import Route53Provider
from osia.installer.dns.base import DNSProvider

DNSProvider.register_provider('nsupdate', NSUpdate)
DNSProvider.register_provider('route53', Route53Provider)
