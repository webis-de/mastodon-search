#!/usr/bin/env python3

from argparse import ArgumentParser
from gzip import GzipFile
from http.client import RemoteDisconnected
from io import BytesIO
from json import dumps, JSONDecodeError, load, loads
from mastodon import (
        Mastodon,
        MastodonAPIError, MastodonNetworkError,
        MastodonNotFoundError, MastodonVersionError
)
from os import makedirs
from sys import exit, stderr, stdout
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

def get_instance_response(instance: str) -> [str, str]:
    """Retrieve Mastodon API data from `instance`: [v1_data, v2_data]"""
    data = []
    # convert IRI to URI (international symbols to "xn--…")
    instance = instance.encode('idna').decode()
    try:
        with (
                urlopen(f'https://{instance}/api/v1/instance', timeout=30)
                    as response_v1,
                urlopen(f'https://{instance}/api/v2/instance', timeout=30)
                    as response_v2
        ):
            for response in response_v1, response_v2:
                # At least 1 instance sends gzipped data. Decompress that.
                if response.info().get('Content-Encoding') == 'gzip':
                    f = GzipFile(fileobj=BytesIO(response.read()))
                    data.append(loads(f.read().decode(errors='replace')))
                # Plaintext
                elif not response.info().get('Content-Encoding'):
                    data.append(loads(response.read().decode(errors='replace')))
                # If there's some other encoding/compression, we need to
                # implement that. But there hasn't been one yet.
                else:
                    print(response.info().get('Content-Encoding'))
                    exit(1)
    # Lots of different errors, mostly when it's not Mastodon. Some instances
    # send a 503 (HTTPError), some just disconnect and some send a small
    # placeholder webpage (JSONDecodeError).
    except (RemoteDisconnected, HTTPError, JSONDecodeError, TimeoutError, URLError):
        return ['', '']
    return data

def get_instances_data_directly(instance_file: str, output_file: str) -> None:
    """Read an instance list from a JSON file in `instance_file`, query all instances
    and save the data to a file.
    """
    instances = get_instance_list(instance_file)
    last_instance_done = get_last_instance_done(output_file)
    # Get data
    with open(output_file, 'a') as file:
        for instance in instances:
            if(instance <= last_instance_done):
                continue
            dic = {}
            print(f'\r{instance}                                    ', end='')
            dic[1], dic[2] = get_instance_response(instance)
            file.write(f'{instance} {dumps(dic)}\n')
        print()

def get_instances_data_mastodon(instance_file: str, output_file: str) -> None:
    """Read an instance list from a JSON file in `instance_file`, query all
    instances for `nodeinfo` and `instance/activity` and save the data to a
    file.
    """
    instances = get_instance_list(instance_file)
    last_instance_done = get_last_instance_done(output_file)
    # Get data
    with open(output_file, 'a') as file:
        for instance in instances:
            if(instance <= last_instance_done):
                continue
            print(f'\r{instance}                                    ', end='')
            try:
                mastodon = Mastodon(api_base_url=instance)
                nodeinfo = mastodon.instance_nodeinfo()
            # {Index,Value}Error occur if the Mastodon version looks "weird",
            # e. g. if it's not actually a Mastodon server.
            except (
                    IndexError, MastodonNetworkError,
                    MastodonVersionError, ValueError
            ):
                file.write(f'{instance} \n')
                continue
            try:
                activity = mastodon.instance_activity()
            except (MastodonNotFoundError, MastodonAPIError):
                activity = []
            dic = {'nodeinfo': nodeinfo, 'activity': activity}
            # Replace datetime.datetime objects by ISO strings so we can write
            # it to file as JSON.
            for entry in dic['activity']:
                entry['week'] = str(entry['week'])
            file.write(f'{instance} {dumps(dic)}\n')
        print()

def get_instance_list(instance_file: str) -> list:
    """Read JSON file and return a list of instances."""
    try:
        with open(instance_file, 'r') as f:
            return load(f)
    except FileNotFoundError:
        print(f'File not found: {instance_file}', file=stderr)
        exit(1)
    except JSONDecodeError:
        print(f'File does not contain valid JSON: {instance_file}', file=stderr)
        exit(1)

def get_last_instance_done(output_file: str) -> list:
    """Return the last (bottom-most) instance that was saved to the file."""
    try:
        with open(output_file, 'r') as file:
            for line in file:
                pass
            return line.split(' ', maxsplit=1)[0]
    except (FileNotFoundError, UnboundLocalError):
        return ''


parser = ArgumentParser(description='Read a JSON file containing mastodon \
        instances and query them for their data.')
parser.add_argument('instance_file', help='File containing a single JSON \
        array with all the instances')
parser.add_argument('output_file', help='File where instance data is saved')
parser.add_argument(
        '-d', '--direct', action='store_true', default=False,
        help='Query API v1 and v2 directly instead of using Mastodon.py .')
args = parser.parse_args()
if(args.direct):
    get_instances_data_directly(args.instance_file, args.output_file)
else:
    get_instances_data_mastodon(args.instance_file, args.output_file)
