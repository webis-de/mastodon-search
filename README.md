[![CI status](https://img.shields.io/github/actions/workflow/status/webis-de/mastodon-search/ci.yml?branch=main&style=flat-square)](https://github.com/webis-de/mastodon-search/actions/workflows/ci.yml)
[![Maintenance](https://img.shields.io/maintenance/yes/2024?style=flat-square)](https://github.com/webis-de/mastodon-search/graphs/contributors)
[![Issues](https://img.shields.io/github/issues/webis-de/mastodon-search?style=flat-square)](https://github.com/webis-de/mastodon-search/issues)
[![Pull requests](https://img.shields.io/github/issues-pr/webis-de/mastodon-search?style=flat-square)](https://github.com/webis-de/mastodon-search/pulls)
[![Commit activity](https://img.shields.io/github/commit-activity/m/webis-de/mastodon-search?style=flat-square)](https://github.com/webis-de/mastodon-search/commits)
[![License](https://img.shields.io/github/license/webis-de/mastodon-search?style=flat-square)](LICENSE)

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
Because the streaming API is unavailable on many instances, our crawler gracefully falls back to using regular HTTP `GET` requests with the [public timeline API](#TODO).

#### Obtaining and analyzing instance data

An initial list of nodes can be obtained from <https://nodes.fediverse.party/>:

```shell
wget https://nodes.fediverse.party/nodes.json
```

Now, enrich the list of instances with global and weekly activity stats.
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

### Docker image

Our code can also run in a container.
First, build the image with this command:

```shell
docker build -t mastodon_search .
```

To run commands using the Docker image just created, replace the `mastodon-search` command from the previous sections with `docker run mastodon_search`.
If you want to save statuses to an Elasticsearch running on your `localhost`, the command should look like the following code snippet.
(You can leave out `--network=host` if it's not on your local machine.)

```shell
docker run --network host mastodon_search stream-to-es --host http://localhost --username es_username --password es_password mastodon.example.com
```

## Deployment

Crawling can be parallelized on a [Kubernetes](#TODO) cluster.
To do so, install [Helm](https://helm.sh/docs/intro/quickstart/) and configure `kubectl` for your cluster.

You are then ready to deploy the Helm chart on the cluster and start the crawling:

```shell
helm install --dry-run --set esUsername="<REDACTED>" --set esPassword="<REDACTED>" --set-file instances="./data/instances.txt" mastodon-crawler ./helm
```

If the above command worked and the Kubernetes resources to be deployed look good to you, just remove the `--dry-run` flag to actually deploy the crawlers.

To stop the crawling, just uninstall the Helm chart:

```shell
helm uninstall mastodon-crawler
```

To re-start the crawling, first uninstall and then re-install the Helm chart.

## Development

First, install [Python 3.11](https://python.org/downloads/) or higher and then clone this repository.
From inside the repository directory, create a virtual environment and activate it:

```shell
python3.11 -m venv venv/
source venv/bin/activate
```

Then, install the test dependencies:

```shell
pip install -e .[tests]
```

After having implemented a new feature, please check the code format, inspect common LINT errors, and run all unit tests with the following commands:

```shell
ruff .                         # Code format and LINT
# mypy .                         # Static typing
bandit -c pyproject.toml -r .  # Security
pytest .                       # Unit tests
```

## Contribute

If you have found a bug in this crawler or feel some feature is missing, please create an [issue](https://github.com/webis-de/mastodon-search/issues). We also gratefully accept [pull requests](https://github.com/webis-de/mastodon-search/pulls)!

If you are unsure about anything, post an [issue](https://github.com/webis-de/mastodon-search/issues/new) or contact us:

- [heinrich.merker@uni-jena.de](mailto:heinrich.merker@uni-jena.de)

We are happy to help!

## Further resources

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

## License

This repository is released under the [MIT license](LICENSE).
