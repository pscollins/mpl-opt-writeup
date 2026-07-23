# Environment setup

## General Python

To build the virtualenv and install dependencies:
```
$ python3 -m venv env
$ . env/bin/activate
$ pip install -r requirements.txt
```

## Chameleon
Initial setup:
```
$ ccauth login
$ source ./CHI-251524-openrc.sh
$ ccauth clouds-yaml --all-sites --all-projects --output ./clouds.yaml
$ source ./chameleon_env.sh
$ openstack keypair create --public-key ~/.ssh/id_ed25519.pub mpl-testing
```

Now, before each use:
```
$ source ./chameleon_env.sh
```

TODO: pick a machine family

To create a new reservation:
```
$ ./reserve_machine.sh
$ ./prepare_machine.sh
```

When done, be sure to release any reserved IPs:
```
# Find allocated IPs
$ openstack floating ip list
# Free up the newly-allocated one
$ openstack floating ip delete $IP
```

# Usage

To activate the virtualenv:
```
$ . env/bin/activate
```

To run the jupyter notebook (and load over GCP):
```
$ jupyter lab --ip=0.0.0.0 --port=8080 --no-browser
```
