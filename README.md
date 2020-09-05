# OSIA

OpenShift infra automation.

## Goal

The tool aims to unified installer of OpenShift to various clouds which is
easy to automate and use within CI.

To see necessary steps for OpenShift installation please see [OpenShift documentation](https://docs.openshift.com).

To see full documentation of `osia` please follow to [Official documentation](https://redhat-cop.github.io/osia).

## Installation

To get started with osia, just install available package from [pypi](pypi.org):

```bash
$ pip install osia
```


__Main features__

* Find empty region in aws to install opneshift on.
* Find feasible network in OpenStack and allocate FIPs before installation happens.
* Generate `install-config.yaml` from predefined defaults.
* Store generated files for deletion to git repository and push changes right after the cluster is installed.
* Manage DNS entries based on the installation properties and results.
* Clean everything once the cluster is not needed.




## Usage

The tool operates over directory which is expected to be git repository and where the service will
store generated configuration and push it to the upstream repository of currently working branch.

### Common configuration

The common configuraiton is done by yaml file called `settings.yaml` that should be located at
`CWD` (root of the repository in most cases).

The configuration has following structure:

```
default:
  cloud:
    openstack:
      base_domain: ''
      certificate_bundle_file: ''
      pull_secret_file: ''
      ssh_key_file: ''
      osp_cloud: ''
      osp_base_flavor: ''
      network_list: []
    aws:
      base_domain: ''
      pull_secret_file: ''
      certificate_bundle_file: ''
      ssh_key_file: ''
      worker_flavor: '' 
      list_of_regions: []
  dns:
    route53:
      ttl: 0
    nsupdate:
      server: ''
      zone: ''
      key_file: ''
      ttl: 0 
```

Every key here is overridible by the argument passed to the installer.
For explanation of any key, please check he documentation below.

