"""Define a common Mastodon status in Elasticsearch DSL."""

from datetime import datetime
from elasticsearch_dsl import (
    Boolean, Date, Document, Float, InnerDoc,
    Integer, Keyword, Nested, Object, Text
)

class Account(InnerDoc):
    # acct is handle@instance
    acct: str = Keyword()
    avatar: str = Text()
    bot: bool = Boolean()
    display_name: str = Text()
    followers_count: int = Integer()
    following_count: int = Integer()
    group: bool = Boolean()
    id: str = Keyword()
    statuses_count: int = Integer()
    url: str = Text()
    username: str = Keyword()

class Application(InnerDoc):
    name: str = Keyword()
    website: str = Text()

# A teaser of linked content.
class Card(InnerDoc):
    description: str = Text()
    height: int = Integer()
    image: str = Text()
    language: str = Keyword()
    provider_name: str = Text()
    type: str = Keyword()
    title: str = Text()
    url: str = Text()
    width: int = Integer()

class Emoji(InnerDoc):
    # Emojis are custom emojis per instance. The URL shows where one can find
    # them. They are used in a status by writing :shortcode: .
    shortcode: str = Keyword()
    url: str = Text()

# Meta information of every MediaAttachment.
class Meta(InnerDoc):
    aspect: float = Float()
    height: int = Integer()
    width: int = Integer()

class MediaAttachment(InnerDoc):
    description: str = Text()
    id: str = Keyword()
    preview_url: str = Text()
    type: str = Keyword()
    url: str = Text()

    meta: Meta = Object(Meta)

    def set_meta(self, aspect, height, width):
        self.meta = Meta(aspect=aspect, height=height, width=width)

class Mention(InnerDoc):
    acct: str = Keyword()
    id: str = Keyword()
    url: str = Text()
    username: str = Keyword()

# An option of a poll
class Option(InnerDoc):
    title: str = Text()
    votes_count: int = Integer()

class Poll(InnerDoc):
    expires_at: datetime = Date()
    id: str = Keyword()
    # Whether multiple selection is allowed
    multiple: bool = Boolean()
    voters_count: int = Integer()

    options: list[Option] = Nested(Option)

    def add_option(self, title, votes_count) -> None:
        self.options.append(Option(title=title, votes_count=votes_count))

# Reblog is a reference to another status that was boosted ("retweeted")
class Reblog(InnerDoc):
    id: str = Keyword()
    url: str = Text()

class Status(Document):
    account: Account = Object(Account)
    # Custom attribute
    api_url: str = Text()
    # Which application was used to post this status
    application: Application = Object(Application)
    card: Card = Object(Card)
    content: str = Text()
    crawl_method = Keyword()
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
    tags: list[str] = Keyword(multi=True)
    uri: str = Text()
    url: str = Text()
    visibility: str = Keyword()

    emojis: list[Emoji] = Nested(Emoji)
    media_attachments: list[MediaAttachment] = Nested(MediaAttachment)
    mentions: list[Mention] = Nested(Mention)

    class Index:
        name = 'corpus_mastodon_statuses'

    def add_emoji(self, shortcode, url) -> None:
        self.emojis.append(Emoji(shortcode=shortcode, url=url))

    def add_media_attachment(self, description, id, meta, preview_url, type, url) -> None:
        """meta should be the original dict that Mastodon.py gives: with an
        'original' entry that itself is a dict containing 'aspect', 'height'
        and 'width' as integers.
        """
        ma = MediaAttachment(description=description, id=id,
            preview_url=preview_url, type=type, url=url)
        if (meta):
            if (orig := meta.get('original')):
                ma.set_meta(
                    orig.get('aspect'), orig.get('height'), orig.get('width'))
        self.media_attachments.append(ma)

    def add_mention(self, acct, id, url, username) -> None:
        self.mentions.append(
            Mention(acct=acct, id=id, url=url, username=username))

    def set_account(
        self, acct, avatar, bot, display_name, followers_count,
        following_count, group, id, statuses_count, url, username
    ) -> None:
        self.account = Account(
            acct=acct,
            avatar=avatar,
            bot=bot,
            display_name=display_name,
            followers_count=followers_count,
            following_count=following_count,
            group=group,
            id=id,
            statuses_count=statuses_count,
            url=url,
            username=username
        )

    def set_application(self, application: dict) -> None:
        self.application = Application(
            name=application.get('name'), website=application.get('website'))

    def set_card(
        self, description, height, image, language,
        provider_name, type, title, url, width
    ) -> None:
        self.card = Card(
            description=description,
            height=height,
            image=image,
            language=language,
            provider_name=provider_name,
            type=type,
            title=title,
            url=url,
            width=width
        )

    def set_poll(
            self, expires_at, id, multiple, options, voters_count) -> None:
        """options should be a list of dicts, each dict being one vote option
        like this: {'title': 'Choice 1', 'votes_count': 0}
        (the default in Mastodon.py).
        """
        poll = Poll(expires_at=expires_at, id=id, multiple=multiple,
            voters_count=voters_count)
        for option in options:
            poll.add_option(option.get('title'), option.get('votes_count'))
        self.poll = poll

    def set_reblog(self, id, url) -> None:
        self.reblog = Reblog(id=id, url=url)
