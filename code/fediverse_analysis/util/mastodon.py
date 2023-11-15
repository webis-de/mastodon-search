from elasticsearch_dsl import Date, Document, InnerDoc, Nested, Text


class Account(InnerDoc):
    acct = Text()


class MediaAttachment(InnerDoc):
    description = Text()
    type_ = Text()
    url = Text()


class Status(Document):
    """Defines a common Mastodon status."""
    content = Text()
    created_at = Date()
    id = Text()
    in_reply_to_id = Text()
    instance = Text()
    language = Text()
    spoiler_text = Text()

    account = Nested(Account)
    media_attachments = Nested(MediaAttachment)

#    class Index:
#        name = 'mastodon'

    def add_media_attachment(self, description, type_, url, commit=False):
        media_attachment = MediaAttachment(
            description=description, type_=type_, url=url)
        self.media_attachments.append(media_attachment)
        if commit:
            self.save()
        return media_attachment

    def set_account(self, acct, commit=False):
        self.account = Account(acct=acct)
        if commit:
            self.save()
        return self.account
