import mastodon as mstdn
from elasticsearch import AuthenticationException
from elasticsearch_dsl import connections, Index
from json import dumps
from sys import exit
from typing import TextIO

from fediverse_analysis.util.mastodon import Status


class Streamer:
    """Leverage Mastodon.py to retrieve data from a Mastodon instance."""
    _ACCOUNT = 'account'
    _ACCT = 'acct'
    _CONTENT = 'content'
    _CREATED_AT = 'created_at'
    _DESCRIPTION = 'description'
    _ID = 'id'
    _IN_REPLY_TO_ID = 'in_reply_to_id'
    _LANGUAGE = 'language'
    _LAST_STATUS_AT = 'last_status_at'
    _MEDIA_ATTACHMENTS = 'media_attachments'
    _REPLIES_COUNT = 'replies_count'
    _SPOILER_TEXT = 'spoiler_text'
    _TYPE = 'type'
    _URL = 'url'


    def __init__(self, instance: str) -> None:
        """Arguments:
        instance -- an instance's base URI, e. g.: 'pawoo.net'.
        """
        self.es_connection = None
        self.es_index = None
        self.instance = instance
        self.output_file = None

        self.mastodon = mstdn.Mastodon(api_base_url=self.instance)

    def _write_status(self, status: dict) -> None:
        """Write an ActivityPub status to the previously defined output."""
        if (self.output_file):
            # Replace datetime objects with strings.
            status[Streamer._CREATED_AT] = str(status[Streamer._CREATED_AT])
            for key in (Streamer._CREATED_AT, Streamer._LAST_STATUS_AT):
                status[Streamer._ACCOUNT][key] = str(
                    status[Streamer._ACCOUNT][key])
            self.output_file.write(dumps(status, ensure_ascii=False) + '\n')
        # Elasticsearch
        else:
            dsl_status = Status(
                content = status.get(Streamer._CONTENT),
                created_at = status.get(Streamer._CREATED_AT),
                id = status.get(Streamer._ID),
                in_reply_to_id = status.get(Streamer._IN_REPLY_TO_ID),
                instance = self.instance,
                language = status.get(Streamer._LANGUAGE),
                spoiler_text = status.get(Streamer._SPOILER_TEXT)
            )
            dsl_status.set_account(
                status.get(Streamer._ACCOUNT).get(Streamer._ACCT))
            for ma in status.get(Streamer._MEDIA_ATTACHMENTS):
                dsl_status.add_media_attachment(
                    ma[Streamer._DESCRIPTION],
                    ma[Streamer._TYPE],
                    ma[Streamer._URL]
                )
            dsl_status.save()

    def _stream_local_updates(self) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public, local statuses.
        """
        while True:
            try:
                self.mastodon.stream_public(
                    _UpdateStreamListener(self), local=True)
            except mstdn.MastodonVersionError:
                print(f'{self.instance} does not support streaming.')
                exit(1)
            except mstdn.MastodonNetworkError as e:
                # Server closes connection, we reconnect.
                # Sadly, there are multiple causes that trigger this error.
                if (str(e) == 'Server ceased communication.'):
                    pass
                else:
                    print(e)
                    exit(1)

    def stream_updates_to_file(self, file: TextIO) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses as JSON Lines to a file.
        """
        self.output_file = file
        self._stream_local_updates()
        self.output_file = None

    def stream_updates_to_es(
        self,
        host: str,
        index: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        """Connect to the streaming API of the Mastodon instance and receive
        new public statuses. Write the statuses to Elasticsearch.
        """
        es_host = host + ':' + str(port)
        try:
            self.es_connection = connections.create_connection(
                hosts=es_host, basic_auth=(username, password))
        except ValueError:
            print(e)
            exit(1)
        self.es_connection.ping()
        self.index = Index(index)
        self.index.document(Status)
        try:
            if (not self.index.exists(self.es_connection)):
                self.index.create(self.es_connection)
        except AuthenticationException as e:
            print('Authentication failed. Wrong username and/or password.')
            exit(1)
        self._stream_local_updates()
        self.es_connection = None


class _UpdateStreamListener(mstdn.StreamListener):
    """Provide own methods for when something happens with a connected
    stream.
    """
    def __init__(self, crawler: Streamer) -> None:
        self.crawler = crawler

    def on_update(self, status) -> None:
        self.crawler._write_status(status)
