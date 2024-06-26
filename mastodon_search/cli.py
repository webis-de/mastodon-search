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
    from mastodon_search.instance_data import analyze
    an = analyze.Analyzer(file)
    an.correlate()

@main.command(
    help='Analyze Mastodon instance nodeinfo and activity data to sample '
        +'instances to crawl. This fits log-normal distribution to the '
        +'instance data values and uses the resulting probability density '
        +'functions as weights for sampling.\n\n'
        +'INPUT_FILE should be the output of the `obtain_instance_data` '
        +'command. The sample including all data is written as csv to '
        +'OUT_FILE_FULL, the pure instance list without anything else written'
        +'to OUT_FILE_PURE.',
    short_help='Sample Mastodon instances to crawl.',
)
@click.argument('input_file', type=click.File('r'), required=True)
@click.argument('output_file_full', type=click.File('w+'), required=True)
@click.argument('output_file_pure', type=click.File('w+'), required=True)
def choose_instances(input_file, output_file_full, output_file_pure):
    from mastodon_search.instance_data import analyze
    an = analyze.Analyzer(input_file)
    an.choose(output_file_full, output_file_pure)

@main.command(
    help='Read an instance list from INPUT_FILE, query all instances for '
        +'`nodeinfo` and `activity` and save the data to OUTPUT_FILE. '
        +'INPUT_FILE should be a single JSON array, for example this file: '
        +'https://nodes.fediverse.party/nodes.json . Data is appended to '
        +'OUTPUT_FILE; the bottom-most instance is read, this program will '
        +'resume from there.'
        +'\n\nAlternatively, use the output of this command as input and do '
        +'multiple runs which will notably increase the amount of instances '
        +'with data present.',
    short_help='Obtain data from fediverse instances.',
)
@click.argument('input_file', type=click.File('r'), required=True)
@click.argument('output_file', type=click.Path(
    dir_okay=False, writable=True), required=True)
def obtain_instance_data(input_file, output_file):
    from mastodon_search.instance_data import obtain
    obtainer = obtain.Obtainer(input_file, output_file)
    obtainer.get_instances_data()

@main.command(
    help='Connect to the streaming API of INSTANCE (e. g.: mastodon.cloud) '
        +'and save incoming new statuses to Elasticsearch (ES). Use crawling '
        +'of the API via GET requests as a fallback since streaming is '
        +'usually not publicly allowed.',
    short_help='Stream instance updates to Elasticsearch.'
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
    from mastodon_search.crawl import stream
    streamer = stream.Streamer(instance)
    streamer.stream_updates_to_elastic(host, password, port, username)
