class MailuoError(Exception):
    """Base class for errors that are safe to map at the API boundary."""


class MailuoForbiddenError(MailuoError):
    pass


class MailuoConfigurationError(MailuoError):
    pass


class MailuoDatabaseError(MailuoError):
    pass


class MailuoEmbeddingError(MailuoError):
    pass


class MailuoSearchError(MailuoError):
    pass
