Installation
============

In order to successfully install this program and run it you need folowing dependencies:

* `python3` and `pip`
* `git` for the management of installation files
* `nsupdate` for management of DNS for openstack installation

For installation just find the newest release at
[tbd]() and find the python
package there. After download just install it via 

```
$ pip install tbd
```

## Docker image

As of version `v0.1.4`, there are also docker images available in `quay.io`.
The images are stored in repository called _tbd_ and there are always two images per release

* `osia-ubi7` docker image based on top of Universal Base Image for rhel 7
* `osia-ubi8` docker image based on top of Universal Base Image for rhel 8

The newest release is always pushed also under the tag `latest`

Example:

```
docker pull tbd
```

Those docker images doesn't have any kind of entrypoint or cmd ready. It is expected that they will be used
as automation platform, if needed the image can be simply extended.
