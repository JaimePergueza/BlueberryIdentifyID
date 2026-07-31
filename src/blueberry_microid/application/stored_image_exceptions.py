from blueberry_microid.application.exceptions import NotFoundError


class StoredImageUnavailableError(NotFoundError):
    """Persisted image content is missing or outside approved storage roots."""
