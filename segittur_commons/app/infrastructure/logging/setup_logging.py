import json
import logging
import os
import sys
from logging.config import dictConfig
from typing import Dict, Any


class JsonFormatter(logging.Formatter):

    SKIP_LIST = (
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "id",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "message",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    )

    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in self.SKIP_LIST and not key.startswith("_"):
                log_record[key] = value

        return json.dumps(log_record, default=str)


def setup_logging(loggers: Dict[str, Any]):
    log_level = os.getenv("LOGGING_LEVEL", "INFO").upper()
    graylog_host = os.getenv("GRAYLOG_HOST")
    graylog_port_str = os.getenv("GRAYLOG_PORT")

    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "[%(levelprefix)s] [%(name)s] %(message)s"},
            "service_formatter": {
                "format": "[%(asctime)s] [%(levelname)s] [service: pid-s08-avc] [module: %(name)s] %(message)s"
            },
            "gelf": {
                "()": JsonFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "service_formatter",
                "stream": sys.stdout,
            },
            "gelf_console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "gelf",
                "stream": sys.stdout,
            },
        },
        "loggers": loggers,
    }

    if graylog_host and graylog_port_str:
        try:
            graylog_port = int(graylog_port_str)

            config["handlers"]["graylog"] = {
                "class": "graypy.GELFUDPHandler",
                "host": graylog_host,
                "port": graylog_port,
                "level": log_level,
            }
            for logger in loggers.keys():
                config["loggers"][logger]["handlers"].append("graylog")

        except (ValueError, TypeError) as e:
            logging.basicConfig(level=logging.WARNING)
            logging.warning(f"The Graylog handler could not be configured: {e}")

    dictConfig(config)
