"""Define a common Mastodon status in Elasticsearch DSL."""

from datetime import datetime
from elasticsearch_dsl import (
    Boolean, Date, Document, InnerDoc, Integer, Keyword, Nested, Object, Text)

class Account(InnerDoc):
    # acct is handle@instance
    acct: str = Keyword()
    display_name: str = Text()
    id: str = Keyword()
    url: str = Text()
    username: str = Keyword()

class Emoji(InnerDoc):
    # Emojis are custom emojis per instance. The URL shows where one can find
    # them. They are used in a status by writing :shortcode: .
    shortcode: str = Keyword()
    url: str = Text()

class MediaAttachment(InnerDoc):
    description: str = Text()
    type: str = Text()
    remote_url: str = Text()
    url: str = Text()

class Mention(InnerDoc):
    acct: str = Keyword()
    id: str = Keyword()
    url: str = Text()

# An option of a poll
class Option(InnerDoc):
    title: str = Text()
    votes_count: int = Integer()

class Poll(InnerDoc):
    expires_at: datetime = Date()
    # Whether multiple selection is allowed
    multiple: bool = Boolean()
    voters_count: int = Integer()

    options = Nested(Option)

    def add_option(self, title, votes_count) -> None:
        self.options.append(Option(title=title, votes_count=votes_count))

# Reblog is a reference to another status that was boosted ("retweeted")
class Reblog(InnerDoc):
    id: str = Keyword()
    url: str = Text()

class Status(Document):
    account: Account = Object(Account)
    # What application was used to post this status
    application: str = Keyword()
    content: str = Text()
    created_at: datetime = Date()
    edited_at: datetime = Date()
    id: str = Keyword()
    in_reply_to_account_id: str = Keyword()
    in_reply_to_id: str = Keyword()
    # Custom attribute: the instance which the status originates from
    instance: str = Keyword()
    language: str = Keyword()
    # Custom attribute
    last_seen: datetime = Date()
    poll: Poll = Object(Poll)
    reblog: Reblog = Object(Reblog)
    # On media: Indicates NSFW. / Activates click to show.
    sensitive: bool = Boolean()
    spoiler_text: str = Text()
    tags: str = Keyword(multi=True)
    uri: str = Text()
    url: str = Text()
    visibility: str = Keyword()

    emojis = Nested(Emoji)
    media_attachments = Nested(MediaAttachment)
    mentions = Nested(Mention)

    class Index():
        name = 'corpus_mastodon_statuses'

    def add_emoji(self, shortcode, url) -> None:
        self.emojis.append(Emoji(shortcode=shortcode, url=url))

    def add_media_attachment(self, description, type, url) -> None:
        self.media_attachments.append(
            MediaAttachment(description=description, type=type, url=url))

    def add_mention(self, acct, id, url) -> None:
        self.mentions.append(Mention(acct=acct, id=id, url=url))

    def set_account(self, acct, display_name, id, url, username) -> None:
        self.account = Account(acct=acct, display_name=display_name, id=id,
            url=url, username=username)

    def set_poll(
            self, expires_at, multiple, options, voters_count) -> None:
        """options should be a list of dicts, each dict being one vote option
        like this: {'title': 'Choice 1', 'votes_count': 0}
        (the default in Mastodon.py).
        """
        poll = Poll(expires_at=expires_at, multiple=multiple,
            voters_count=voters_count)
        for option in options:
            poll.add_option(option.get('title'), option.get('votes_count'))
        self.poll = poll

    def set_reblog(self, id, url) -> None:
        self.reblog = Reblog(id=id, url=url)
