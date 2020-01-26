import boto3
from typing import List, Union


from installer.clouds.base import AbstractInstaller


class AWSInstaller(AbstractInstaller):
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
            raise Exception("No free region found")
        self.cluster_region = region

    def post_installation(self):
        pass


def get_free_region(order_list: List[str]) -> Union[str, type(None)]:
    """Finds first free region in provided list, if provided list is empty, it searches all regions"""
    candidates = order_list[:]
    if len(candidates) == 0:
        candidates = [v['RegionName'] for v in boto3.client('ec2').describe_regions()['Regions']]
    for candidate in candidates:
        print(candidate)
        region = boto3.client('ec2', candidate)
        count = len(region.describe_vpcs()['Vpcs'])
        if count < 5:
            return candidate
    return None
