# 🕸️ mastodon-search

A Corpus for Simulating Search on Mastodon.

## Installation

1. Install [Python 3.11](https://python.org/downloads/) or higher.
2. Create and activate a virtual environment:

    ```shell
    python3.11 -m venv venv/
    source venv/bin/activate
    ```

3. Install dependencies:

    ```shell
    pip install -e .
    ```

## Usage

Use this repository to [crawl](#crawling), [analyze](#TODO), and [search](#TODO) Mastodon posts.

Hint: You can always list all available commands of our crawler by running:

```shell
mastodon-search -h
```

### Crawling

#### Crawling a single instance

The central command used to crawl an instance is `stream-to-es`. It opens a connection to the specified Mastodon instance, receives new posts, and stores them in an [Elasticsearch](#TODO) index:

```shell
mastodon-search stream-to-es --host https://es.example.com --username es_username --password es_password mastodon.example.com
```

Behind the scenes, this will fetch posts using Mastodon's [streaming API](#TODO).
Because the streaming API is not available on many instances, our crawler gracefully falls back to using regular HTTP `GET` requests with the [public timeline API](#TODO).

#### Obtaining and analyzing instance data

An initial list of nodes can be obtained from <https://nodes.fediverse.party/>:

```shell
wget https://nodes.fediverse.party/nodes.json
```

Now, let's enrich the list of instances with global and weekly activity stats.
Be aware that the below command can take a few hours to complete:

```shell
mastodon-search obtain-instance-data nodes.json mastodon_instance_data/
```

### Sampling instances for crawling

With the activity stats obtained, we can draw a representative sample out of all the instances:

```shell
mastodon-search choose-instances mastodon_instance_data/ out.csv
```

> TODO: Don't we do this in the notebooks?

### Analyzing

We provide [Jupyter notebooks] for easily analyzing the instances and crawled posts.

To open a notebook, just run, e.g.:

```shell
jupyter notebook notebooks/mastodon-instance-data-vis.ipynb
```

#### Correlation of instance statistics

The correlation between all available instance statistics can be calculated by running:

```shell
mastodon-search calculate-correlation mastodon_instance_data/
```

> TODO: Fix everything below.


### Docker
To run this program in a container, first build the image with this command:
```shell
docker buildx build -t mastodon_search .
```

When running commands in a container, leave out `mastodon-search`, as it is already specified as entrypoint. If you want to save statuses to an Elasticsearch on your localhost, the command will look like this. You might leave out `--network="host"` if it's not on your local machine.
```shell
docker run --network="host" mastodon_search:latest stream-to-es -H 'http://localhost' -u 'username' -P 'p4ssw0rd' 'pawoo.net'
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

## Links

- Standards:
  - [ActivityPub](https://w3.org/TR/activitypub/)
  - [Activity Streams 2.0](https://w3.org/TR/activitystreams-core/) (syntax for activity data)
  - [Activity Vocabulary](https://w3.org/TR/activitystreams-vocabulary/)
  - [WebFinger](https://rfc-editor.org/rfc/rfc7033)
- APIs:
  - [Mastodon-Dokumentation](https://docs.joinmastodon.org/)
- [List of Fediverse nodes](https://nodes.fediverse.party/) ([source code](https://github.com/Minoru/minoru-fediverse-crawler))
- [Liste of Fediverse software](https://github.com/emilebosch/awesome-fediverse)
- Blogs:
  - [Understanding ActivityPub](https://seb.jambor.dev/posts/understanding-activitypub/)
  - [Understanding Mastodon](https://seb.jambor.dev/posts/understanding-activitypub-part-3-the-state-of-mastodon/)
