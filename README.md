# OSIA

OpenShift infra automation

## Goal

The tool aims to create unified installer 

__Main features__

* Find empty region in aws to install opneshift on
* Find feasible network in PSI and allocate FIPs before installation happens
* Generate `install-config.yaml` from predefined defaults.
* Store generated files for deletion to git repository and push changes right after the cluster is installed
* Manage DNS entries based on the installation properties and results
* Clean everything once the cluster is not needed




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

