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
