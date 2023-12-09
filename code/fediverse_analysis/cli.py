import click


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS)
def main():
    pass

@main.command(
    help='Calculate correlation of some Mastodon instance statistics.',
    short_help='Calculate correlation of Mastodon stats.',
)
@click.argument('file', type=click.File('r'))
def calculate_correlation(file):
    from fediverse_analysis.instance_data import analyze
    an = analyze.Analyzer(file)
    an.correlate()

@main.command(
    help='Analyze Mastodon instance activity data to find instances to crawl'
        +'by using stratified sampling.'
        +'RAW_DATA_FILE must contain crawled instance data. If given, this'
        +'program will write the sampled instances to SAMPLE_FILE, one '
        +'instance per line; and the sampled instances plus their data as '
        +'json dump to SAMPLE_FILE_WITH_DATA',
    short_help='Find Mastodon instances to crawl.',
)
@click.argument('raw_data_file', type=click.File('r'), required=True)
@click.argument('sample_file', type=click.File('w+'), required=False)
@click.argument('data_file', type=click.File('w+'), required=False)
@click.option('-s', '--sample-size', default=1000,
    help='How many instances should be chosen. This will differ due to '
    +'rounding. Default: 1000')
def choose_instances(raw_data_file, sample_file, data_file, sample_size, ):
    from fediverse_analysis.instance_data import analyze
    an = analyze.Analyzer(raw_data_file)
    an.stratify(sample_file, data_file, sample_size)

@main.command(
    help='Crawl the API of INSTANCE (e. g.: mastodon.cloud) '
        +'and save new statuses to Elasticsearch (ES).',
    short_help='Crawl instance updates to Elasticsearch.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.option('-H', '--host', required=True,
    help='ES host, e. g.: https://example.com')
@click.option('-P', '--password', default='',
    help='ES password to your username')
@click.option('-p', '--port', default=9200,
    help='Port on which ES listens. Default: 9200')
@click.option('-u', '--username', default='',
    help='Username for ES authentication')
@click.option('-w', '--wait', default=3600,
    help='Max. time to wait between requests in seconds. Default: 3600')
@click.argument('instance')
def crawl_to_es(instance, host, password, port, username, wait):
    from fediverse_analysis.crawl import crawl
    crawler = crawl.Crawler(instance)
    crawler.crawl_to_es(host, password, username, wait, port)

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
    help='Read an instance list from NODES_FILE, query all instances for '
        +'`nodeinfo` and `instance/activity` and save the data to OUT_FILE. '
        +'NODES_FILE should be a single JSON array, for example this file: '
        +'https://nodes.fediverse.party/nodes.json . Data is appended to '
        +'OUT_FILE. The bottom-most instance is read, this program will '
        +'resume from there.',
    short_help='Obtain data from fediverse instances.',
)
@click.argument('nodes_file', type=click.File('r'), required=True)
@click.argument('out_file', type=click.Path(
    dir_okay=False, writable=True), required=True)
def obtain_instance_data(nodes_file, out_file):
    from fediverse_analysis.instance_data import obtain
    obtain.get_instances_data(nodes_file, out_file)


@main.command(
    help='Connect to the streaming API of INSTANCE (e. g.: mastodon.cloud) '
        +'and save incoming new statuses to Elasticsearch (ES). Use crawling '
        +'of the API via GET requests as a fallback since streaming is '
        +'usually not publicly allowed.',
    short_help='Stream instance updates to Elasticsearch.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.option('-H', '--host', required=True,
    help='ES host, e. g.: https://example.com')
@click.option('-P', '--password', default='',
    help='ES password to your username')
@click.option('-p', '--port', default=9200,
    help='Port on which ES listens. Default: 9200')
@click.option('-u', '--username', default='',
    help='Username for ES authentication')
@click.argument('instance')
def stream_to_es(instance, host, password, port, username):
    from fediverse_analysis.crawl import stream
    streamer = stream.Streamer(instance)
    streamer.stream_updates_to_es(host, password, port, username)

@main.command(
    help='Connect to the streaming API of INSTANCE (e. g.: '
        +'mastodon.cloud) and append incoming new statuses to FILE. Use '
        +'crawling of the API via GET requests as a fallback since streaming '
        +'is usually not publicly allowed.',
    short_help='Stream instance updates to a file.',
    epilog='Only `/api/v1/streaming/public/local` is currently implemented.'
)
@click.argument('instance')
@click.argument('file', type=click.File('a'))
def stream_to_file(instance, file):
    from fediverse_analysis.crawl import stream
    streamer = stream.Streamer(instance)
    streamer.stream_updates_to_file(file)
