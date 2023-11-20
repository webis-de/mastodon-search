import click


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS)
def main():
    pass

@main.command(
    help='Crawl the API of INSTANCE (e. g.: mastodon.cloud) '
        +'and save new statuses to Elasticsearch (ES).',
    short_help='Crawl instance updates to Elasticsearch.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.option('-H', '--host', required=True,
    help='ES host, e. g.: https://example.com')
@click.option('-i', '--index', required=True, help='ES index name')
@click.option('-P', '--password', default='',
    help='ES password to your username')
@click.option('-p', '--port', default=9200,
    help='Port on which ES listens. Default: 9200')
@click.option('-u', '--username', default='',
    help='Username for ES authentication')
@click.option('-w', '--wait', default=3600,
    help='Max. time to wait between requests in seconds. Default: 3600')
@click.argument('instance')
def crawl_to_es(instance, host, index, password, port, username, wait):
    from fediverse_analysis.crawl import crawl
    crawler = crawl.Crawler(instance)
    crawler.crawl_to_es(host, index, password, username, wait, port)

@main.command(
    help='Crawl the API of INSTANCE (e. g.: mastodon.cloud) and save new '
        +'statuses to a file. If the file already contains statuses, read the'
        +' last one and start crawling there. This will fetch all missed '
        +'statuses while the crawler was not running.',
    short_help='Crawl instance updates to file.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.option('-w', '--wait', default=3600,
    help='Max. time to wait between requests in seconds. Default: 3600')
@click.argument('instance')
@click.argument('filename', type=click.Path(dir_okay=False, writable=True))
def crawl_to_file(instance, filename, wait):
    from fediverse_analysis.crawl import crawl
    crawler = crawl.Crawler(instance)
    crawler.crawl_to_file(filename, wait)

@main.command(
    help='Connect to the streaming API of INSTANCE (e. g.: mastodon.cloud) '
        +'and save incoming new statuses to Elasticsearch (ES).',
    short_help='Stream instance updates to Elasticsearch.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.option('-H', '--host', required=True,
    help='ES host, e. g.: https://example.com')
@click.option('-i', '--index', required=True, help='ES index name')
@click.option('-P', '--password', default='',
    help='ES password to your username')
@click.option('-p', '--port', default=9200,
    help='Port on which ES listens. Default: 9200')
@click.option('-u', '--username', default='',
    help='Username for ES authentication')
@click.argument('instance')
def stream_to_es(instance, host, index, password, port, username):
    from fediverse_analysis.crawl import stream
    streamer = stream.Streamer(instance)
    streamer.stream_updates_to_es(host, index, password, port, username)

@main.command(
    help='Connect to the streaming API of INSTANCE (e. g.: '
        + 'mastodon.cloud) and append incoming new statuses to FILE.',
    short_help='Stream instance updates to a file.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.argument('instance')
@click.argument('file', type=click.File('a'))
def stream_to_file(instance, file):
    from fediverse_analysis.crawl import stream
    streamer = stream.Streamer(instance)
    streamer.stream_updates_to_file(file)
