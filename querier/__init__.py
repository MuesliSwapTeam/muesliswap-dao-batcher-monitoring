import logging.config
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
# custom loglevel for benchmarks (debug=10, info=20)
LOG_BENCH = 15

OGMIOS_HOSTNAME = os.environ.get("OGMIOS_HOSTNAME", "localhost")


logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
        "formatters": {
            "full": {"format": "[%(asctime)s] %(levelname)-8s %(name)s %(message)s"},
            "short": {"format": "%(levelname)s %(name)s %(message)s"},
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "full",
            },
            "warn_console": {
                "level": "WARNING",
                "class": "logging.StreamHandler",
                "formatter": "full",
            },
            "out": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "short",
            },
            "err_file": {
                "level": "WARNING",
                "class": "logging.FileHandler",
                "filename": f"{LOG_DIR}/errors.log",
                "formatter": "short",
            },
            "log_file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "filename": f"{LOG_DIR}/full.log",
                "formatter": "full",
            },
        },
        "loggers": {
            # loggers for our own modules
            "querier": {
                "level": "DEBUG",
                "handlers": ["console", "err_file", "log_file"],
                "propagate": False,
            },
            "__main__": {
                "level": "DEBUG",
                "handlers": ["console", "err_file", "log_file"],
                "propagate": False,
            },
            # for some reason, changing the log-level here does not work
            "sqlalchemy.engine.Engine": {
                "level": "WARNING",
                "handlers": ["warn_console"],
                "propagate": False,
            },
        },
        # root logger controlling imports
        "root": {
            "level": "WARNING",
            "handlers": ["console"],
        },
    }
)
