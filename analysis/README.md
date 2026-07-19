# Environment setup

To build the virtualenv and install dependencies:
```
$ python3 -m venv env
$ . env/bin/activate
$ pip install -r requirements.txt
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
