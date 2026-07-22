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
```

Now, before each use:
```
$ source ./chameleon_env.sh
```

TODO: pick a machine family

To create a new reservation:
```

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
