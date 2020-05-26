# Setup guide

The main aim of osia, is to support automation necessary for quick deployment and destruction of clusters usable 
especially in CI process. That's why osia tool leverages the Git VCS to store all of the artifacts created by the
OpenShift installation. Osia tool therefore expects the git repository as the place where it is started, and where all
of the service files will be persisted. 

In order to start you should create git repository by simple running

```
mkdir my_clusters
git init
```

By those steps you will have a git repository ready for your usage. 
The next necessary step would be to setup the remote tracking repository.


## Configuration file

The configuration file is in format of `yaml` and it is expected to hold default
values for install
