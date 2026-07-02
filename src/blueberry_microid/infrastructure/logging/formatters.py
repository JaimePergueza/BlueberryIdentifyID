import json
import logging

# Fields our own log calls attach via `extra={...}`. Third-party loggers
# (uvicorn, sqlalchemy, ...) won't have these, so both formatters below use
# `getattr(record, key, None)` rather than a raw `%(key)s` format string,
# which would raise if the attribute is missing on a given record.
_STRUCTURED_FIELDS = ("request_id", "method", "path", "status_code", "duration_ms", "exception_type")


class JsonLogFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, message, plus any of the
    structured request fields present on that particular record.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _STRUCTURED_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class ConsoleLogFormatter(logging.Formatter):
    """Human-readable single-line format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        base = f"{self.formatTime(record, '%Y-%m-%dT%H:%M:%S')} {record.levelname:<8} {record.name}: {record.getMessage()}"
        extras = [
            f"{key}={value}"
            for key in _STRUCTURED_FIELDS
            if (value := getattr(record, key, None)) is not None
        ]
        if extras:
            base += " [" + " ".join(extras) + "]"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base
