import abc
import os
from lib.config import config


class Singleton(abc.ABC):
    _instance = None
    _initialized = os.path.exists(
        os.path.join(
            config.root_dir,
            config.vcs_dir,
        )
    )

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__(cls)
        return cls._instance
