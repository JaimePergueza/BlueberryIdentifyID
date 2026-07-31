from blueberry_microid.application.exceptions import ApplicationError, ConflictError, NotFoundError


class AuthenticationError(ApplicationError):
    """Base class for controlled authentication failures."""


class InvalidCredentialsError(AuthenticationError):
    """Username/password did not authenticate; message must remain generic."""


class AuthenticationRequiredError(AuthenticationError):
    """A bearer session is missing, expired, revoked, or belongs to an inactive user."""


class PermissionDeniedError(AuthenticationError):
    """The authenticated role cannot perform the requested operation."""


class UserNotFoundError(NotFoundError):
    """An administrator referenced a user that does not exist."""


class DuplicateUsernameError(ConflictError):
    """A normalized username is already registered."""


class LastActiveAdminError(ConflictError):
    """The operation would remove or deactivate the last active administrator."""
