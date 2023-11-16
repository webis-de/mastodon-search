from elasticsearch_dsl import connections, Index
from json import dumps

from fediverse_analysis.util.mastodon import Status


class _Save:
    """Provide methods to store ActivityPub data on disk."""
    ACCOUNT = 'account'
    ACCT = 'acct'
    CONTENT = 'content'
    CREATED_AT = 'created_at'
    DESCRIPTION = 'description'
    ID = 'id'
    IN_REPLY_TO_ID = 'in_reply_to_id'
    LANGUAGE = 'language'
    LAST_STATUS_AT = 'last_status_at'
    MEDIA_ATTACHMENTS = 'media_attachments'
    REPLIES_COUNT = 'replies_count'
    SPOILER_TEXT = 'spoiler_text'
    TYPE = 'type'
    URL = 'url'

    def __init__(self) -> None:
        self.es_connection = None
        self.output_file = None

    def init_es_connection(
        self,
        host: str,
        index: str,
        password: str = '',
        port: int = 9200,
        username: str = ''
    ) -> None:
        es_host = host + ':' + str(port)
        self.es_connection = connections.create_connection(
            hosts=es_host, basic_auth=(username, password))
        index = Index(index)
        index.document(Status)
        if (not index.exists(self.es_connection)):
            index.create(self.es_connection)

    def write_status(self, status: dict, instance: str) -> None:
        """Write an ActivityPub status to the previously defined output."""
        if (self.output_file):
            # Replace datetime objects with strings.
            status[self.CREATED_AT] = str(status[self.CREATED_AT])
            for key in (self.CREATED_AT, self.LAST_STATUS_AT):
                status[self.ACCOUNT][key] = str(
                    status[self.ACCOUNT][key])
            self.output_file.write(dumps(status, ensure_ascii=False) + '\n')
        # Elasticsearch
        else:
            # Put status data into the ES DSL frame.
            dsl_status = Status(
                content = status.get(self.CONTENT),
                created_at = status.get(self.CREATED_AT),
                id = status.get(self.ID),
                in_reply_to_id = status.get(self.IN_REPLY_TO_ID),
                instance = instance,
                language = status.get(self.LANGUAGE),
                spoiler_text = status.get(self.SPOILER_TEXT),
                url = status.get(self.URL)
            )
            dsl_status.set_account(
                status.get(self.ACCOUNT).get(self.ACCT))
            for ma in status.get(self.MEDIA_ATTACHMENTS):
                dsl_status.add_media_attachment(
                    ma[self.DESCRIPTION],
                    ma[self.TYPE],
                    ma[self.URL]
                )
            dsl_status.save()

