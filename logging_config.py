from logging.config import dictConfig

def setup_logging():
    dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(levelname)s (%(asctime)s):      %(message)s",
                "datefmt": "%d-%m-%Y %H:%M:%S",
            },
        },
        "handlers": {
            "default_file": {
                "class": "logging.FileHandler",
                "filename": "application.log",
                "formatter": "default",
                "encoding": "utf-8"
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default"
            },
            "uvicorn_access_file": {
                "class": "logging.FileHandler",
                "filename": "uvicorn_access.log",
                "formatter": "default",
                "encoding": "utf-8"
            },
            "uvicorn_error_file": {
                "class": "logging.FileHandler",
                "filename": "uvicorn_error.log",
                "formatter": "default",
                "encoding": "utf-8"
            },
        },
        "loggers": {
            "": {
                "level": "INFO",
                "handlers": ["default_file", "console"],
            },
            "uvicorn.access": {
                "level": "INFO",
                "handlers": ["uvicorn_access_file"],
                "propagate": False
            },
            "uvicorn.error": {
                "level": "INFO",
                "handlers": ["uvicorn_error_file", "console"],
                "propagate": False
            },
        }
    })
