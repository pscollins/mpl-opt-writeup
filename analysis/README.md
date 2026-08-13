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
$ ccauth clouds-yaml --all-sites --all-projects --output ./clouds.yaml
$ source ./chameleon_env.sh
$ openstack keypair create --public-key ~/.ssh/id_ed25519.pub mpl-testing-$(hostname)
```

Now, before each use:
```
$ source ./chameleon_env.sh
```

To check host capacity before creating a reservation:
```
$ ./check_capacity.sh [--duration=Nh]
```

To create a new reservation:
```
$ ./reserve_machine.sh --duration=Nh [--node-type=<type>]
$ ./prepare_machine.sh
```

To check the status of reserved resources (lease, server, floating IPs):
```
$ ./check_status.sh
```

When done, release all reserved resources (server instance, floating IPs, and lease):
```
$ ./delete_machine.sh
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
