# fediverse_analysis

## Installation

1. Install [Python 3.12](https://python.org/downloads/).
2. (Optional, but highly recommended) Create and activate virtual environment:
    ```shell
    python3.12 -m venv venv/
    source venv/bin/activate
    ```
3. Install dependencies:
    ```shell
    pip install -e .
    ```

## Usage

Run `fediverse_analysis` as module. It will list and explain all available commands:
```shell
python3.12 -m fediverse_analysis -h
```

To stream new statuses from a Mastodon instance to a file, run something like:
```shell
python3.12 -m fediverse_analysis stream-to-file 'pawoo.net' path/to/file
```
For writing incoming status to an Elasticsearch, the command looks something like this:
```shell
python3.12 -m fediverse_analysis stream-to-es -H 'http://example.com' -i 'mastodon' -u 'username' -P 'p4ssw0rd' troet.cafe
```


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
