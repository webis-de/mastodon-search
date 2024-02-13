# fediverse_analysis

## Installation

1. Install [Python 3.12](https://python.org/downloads/).
2. (Optional, but highly recommended) Create and activate virtual environment:
    ```shell
    python3.12 -m venv venv/
    source venv/bin/activate
    ```
3. Install dependencies. To just run the code:
    ```shell
    pip install -e .
    ```

    To also be able to interact with jupyter notebooks:
    ```shell
    pip install -e '.[notebook]'
    ```


## Usage

### Streaming / Crawling
Run `fediverse_analysis` as module. It will list and explain all available commands:
```shell
python3.12 -m fediverse_analysis -h
```

`python3.12 -m fediverse_analysis <command> -h` will display a more in-depth explanation of what the command does. The main command is `stream-to-es`. It opens a connection to a Mastodon instance and receives new statuses which are put to an Elasticsearch instance. Because streaming is not allowed on many instances, it uses GET requests to the API as a fallback. Here is an example:
```shell
python3.12 -m fediverse_analysis stream-to-es -H 'http://example.com' -i 'mastodon' -u 'username' -P 'p4ssw0rd' troet.cafe
```

### Obtaining and analyzing instance data
Data of all instances is already available at `/mnt/ceph/storage/data-in-progress/data-teaching/theses/wstud-thesis-ernst/instance-data/mastodon`. If you want to try it anyway, you need a `nodes.json` first. Beware though, it takes a few hours:
```shell
wget 'https://nodes.fediverse.party/nodes.json'
python -m fediverse_analysis obtain-instance-data nodes.json mastodon_instance_data
```
With this data you can calculate correlation between available statistics or draw a sample out of all the instances:
```shell
python -m fediverse_analysis calculate-correlation '/mnt/ceph/storage/data-in-progress/data-teaching/theses/wstud-thesis-ernst/instance-data/mastodon'
python -m fediverse_analysis choose-instances '/mnt/ceph/storage/data-in-progress/data-teaching/theses/wstud-thesis-ernst/instance-data/mastodon' out.csv
```


### Jupyter Notebooks
Just run `jupyter notebook <notebook-name>`, e. g.:
```shell
jupyter notebook notebooks/mastodon_instance_data_vis.ipynb
```


### Docker
To run this program in a container, first build the image with this command:
```shell
docker buildx build -t fediverse_analysis .
```

When running commands in a container, leave out `python3.12 -m fediverse_analysis`, as it is already specified as entrypoint. If you want to save statuses to an Elasticsearch on your localhost, the command will look like this. You might leave out `--network="host"` if it's not on your local machine.
```shell
docker run --network="host" fediverse_analysis:latest stream-to-es -H 'http://localhost' -u 'username' -P 'p4ssw0rd' 'pawoo.net'
```

### Cluster (Helm/Kubernetes)
Crawling can be parallelized on a Kubernetes cluster.

#### Installation
Install [Helm](https://helm.sh/docs/intro/quickstart/) and configure `kubectl` for your cluster.

#### Deployment

Let's deploy the Helm chart on the cluster to start the crawling:

```shell
helm --namespace wo84xel install --dry-run --set esUsername="<REDACTED>" --set esPassword="<REDACTED>" --set-file instances="./data/instances.txt" mastodon-crawler ./code/helm
```

#### Uninstall

To stop the crawling, you can uninstall the Helm chart:

```shell
helm --namespace wo84xel uninstall mastodon-crawler
```

To re-start the crawling, first uninstall and then re-install the Helm chart.



# Links

## Standards

- [ActivityPub-Spec](https://www.w3.org/TR/activitypub/)
- [Activity Streams](https://www.w3.org/TR/activitystreams-core/) (Syntax für Aktivitäts-Daten)
- [Activity-Streams-Vokabular](https://www.w3.org/TR/activitystreams-vocabulary/)
- [WebFinger](https://www.rfc-editor.org/rfc/rfc7033)


## Crawler

- [Minoru's Fediverse crawler](https://github.com/Minoru/minoru-fediverse-crawler): Stellt eine Liste aller Fediverse-Server zusammen, die online sind
    - [Webseite](https://nodes.fediverse.party/)
    - [`nodes.json`](https://nodes.fediverse.party/nodes.json)


## Sonstiges

- [Liste von Fediverse-Software](https://github.com/emilebosch/awesome-fediverse)
- Understanding [ActivityPub](https://seb.jambor.dev/posts/understanding-activitypub/)/[Mastodon](https://seb.jambor.dev/posts/understanding-activitypub-part-3-the-state-of-mastodon/) (inkl. Flowcharts)
- [Mastodon-Dokumentation](https://docs.joinmastodon.org/)
