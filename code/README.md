# get-instance-data.py

## Requirements

[Mastodon.py](https://mastodonpy.readthedocs.io/en/stable/index.html):
```
$ pip install Mastodon.py
```

## Usage

First, retrieve an instance list like this:
```
$ wget https://nodes.fediverse.party/nodes.json
```
There are two options. Don't mix these up in one output file. To gather `nodeinfo` and `activity` from instances:
```
$ ./get-instance-data.py nodes.json nodes_data_1
```
To gather everything from `/api/v1/instance` and `/api/v2/instance`
```
$ ./get-instance-data.py -d nodes.json nodes_data_2
```
