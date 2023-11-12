import click


_CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=_CONTEXT_SETTINGS)
def main():
    pass


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
    streamer.stream_local_updates(file)
