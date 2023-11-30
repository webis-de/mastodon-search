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

`python3.12 -m fediverse_analysis <command> -h` will display a more in-depth explanation of what the command does. The commands `crawl-to-es` and `stream-to-es` are similar in their usage, as well as `crawl-to-file` and `stream-to-file`. Both streaming commands use crawling as a fallback, because streaming is not allowed on many instances.

To stream new statuses from a Mastodon instance to a file, you might run:
```shell
python3.12 -m fediverse_analysis stream-to-file 'pawoo.net' path/to/file
```
For putting incoming statuses to an Elasticsearch, the command looks something like this:
```shell
python3.12 -m fediverse_analysis stream-to-es -H 'http://example.com' -i 'mastodon' -u 'username' -P 'p4ssw0rd' troet.cafe
```

### Docker

To run this program in a container, first build the image with this command:
```shell
docker buildx build -t fediverse_analysis .
```

When running commands in a container, leave out `python3.12 -m fediverse_analysis`, as it is already specified as entrypoint. If you want to write to a file, use a command similar like the following one. This will effectively write to a file called `outfile` in your specified host dir.
```shell
docker run -v "/absolute/path/to/host/dir/:/workspace/" fediverse_analysis:latest stream-to-file 'pawoo.net' outfile
```
If you want to save statuses to an Elasticsearch on your localhost, the command will look like this. You might leave out `--network="host"` if it's not on your local machine.
```shell
docker run --network="host" fediverse_analysis:latest stream-to-es -H 'http://localhost' -u 'username' -P 'p4ssw0rd' 'pawoo.net'
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
