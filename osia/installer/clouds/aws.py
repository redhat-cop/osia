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
"""Module implements configuration object for aws installation"""
import logging

import boto3
from botocore.exceptions import ClientError

from .base import AbstractInstaller


def _get_connection(*args, **kwargs):
    return boto3.client("ec2", *args, **kwargs)


def _get_quotas_connection(*args, **kwargs):
    return boto3.client("service-quotas", *args, **kwargs)


class AWSInstaller(AbstractInstaller):
    """Object containing all configuration related
    to aws installation"""

    # pylint: disable=too-many-arguments
    def __init__(self, cluster_region=None, list_of_regions=None,
                 aws_access_key_id=None, aws_secret_access_key=None, aws_session_token=None, **kwargs):
        super().__init__(**kwargs)
        self.cluster_region = cluster_region
        self.list_of_regions = list_of_regions if list_of_regions else []

        self.boto_kwargs = {
            "aws_access_key_id": aws_access_key_id,
            "aws_secret_access_key": aws_secret_access_key,
            "aws_session_token": aws_session_token,
        }

    def get_template_name(self):
        return 'aws.jinja2'

    def acquire_resources(self):
        region = self.get_free_region()

        if region is None:
            logging.error("No free region amongst selected ones: %s",
                          ', '.join(self.list_of_regions))
            raise Exception("No free region found")
        logging.info("Selected region %s", region)
        self.cluster_region = region

    def get_api_ip(self) -> str | None:
        return None

    def get_apps_ip(self):
        return None

    def post_installation(self):
        pass

    def get_free_region(self) -> str | None:
        """Finds first free region in provided list,
        if provided list is empty, it searches all regions"""
        candidates = self.list_of_regions[:]
        if len(candidates) == 0:
            candidates = boto3.Session().get_available_regions('ec2')
        for candidate in candidates:
            region = _get_connection(candidate, **self.boto_kwargs)
            try:
                count = len(region.describe_vpcs()['Vpcs'])
                quotas = _get_quotas_connection(candidate, **self.boto_kwargs)
                quota = quotas.get_service_quota(
                    ServiceCode='vpc',
                    QuotaCode='L-F678F1CE',  # VPCs per Region
                )['Quota']['Value']
                if count < quota:
                    logging.debug("Selected region %s", candidate)
                    return candidate
            except ClientError:
                logging.debug("Skipping %s region, it might not be enalbed", candidate)
                continue
        return None
