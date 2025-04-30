from __future__ import annotations

import os
import re
from functools import lru_cache

from blake3 import blake3

from lib.config import config


@lru_cache
def get_object_path(hash: str):
    folder = re.compile(config.root_dir + r"\/?").sub(
        "",
        os.path.join(
            config.objects_dir,
            hash[:2],
        ),
    )
    filename = hash[2:]

    return folder, filename


@lru_cache
def get_head_ref_path(branch: str):
    return os.path.join(config.refs_dir, "heads", branch)


@lru_cache
def get_stash_ref_path(branch: str):
    return os.path.join(config.refs_dir, "stash", branch)


@lru_cache
def get_hash(data: bytes | str):
    return blake3(
        data.encode() if isinstance(data, str) else data,
        max_threads=blake3.AUTO,
    )


@lru_cache
def get_index_filename(data: str):
    return get_hash(data).hexdigest(length=4)
