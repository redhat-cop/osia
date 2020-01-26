from .nsupdate import NSUpdate
from .route53 import Route53Provider
from .base import DNSProvider

DNSProvider.register_provider('nsupdate', NSUpdate)
DNSProvider.register_provider('route53', Route53Provider)
