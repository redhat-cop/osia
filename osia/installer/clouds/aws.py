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
"""Module implements configuration object for aws installation"""
from typing import List, Optional
import logging
import boto3

from .base import AbstractInstaller


class AWSInstaller(AbstractInstaller):
    """Object containing all configuration related
    to aws installation"""
    def __init__(self,
                 cluster_region=None,
                 list_of_regions=None,
                 **kwargs):
        super().__init__(**kwargs)
        self.cluster_region = cluster_region
        self.list_of_regions = list_of_regions if list_of_regions else list()

    def get_template_name(self):
        return 'aws.jinja2'

    def acquire_resources(self):
        region = get_free_region(self.list_of_regions)

        if region is None:
            logging.error("No free region amongst selected ones: %s",
                          ', '.join(self.list_of_regions))
            raise Exception("No free region found")
        logging.info("Selected region %s", region)
        self.cluster_region = region

    def post_installation(self):
        pass


def get_free_region(order_list: List[str]) -> Optional[str]:
    """Finds first free region in provided list,
    if provided list is empty, it searches all regions"""
    candidates = order_list[:]
    if len(candidates) == 0:
        candidates = [v['RegionName'] for v in boto3.client('ec2').describe_regions()['Regions']]
    for candidate in candidates:
        region = boto3.client('ec2', candidate)
        count = len(region.describe_vpcs()['Vpcs'])
        if count < 5:
            logging.debug("Selected region %s", candidate)
            return candidate
    return None
