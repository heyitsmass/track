from __future__ import annotations

import os
import re
import typing as t
from functools import lru_cache

import typing_extensions as te
from pydantic import BaseModel

from lib.abc import Singleton
from lib.config import DIR, FILE, config
from lib.fs import FileSystemTree
from lib.models import IndexSearchResult
from lib.utils import get_hash, get_index_filename, get_object_path

ObjectMode = te.TypeAliasType("ObjectMode", t.Literal["040000", "100644"])

fs = FileSystemTree(root_name=config.root_dir)


class HeadMeta(t.NamedTuple):
    root: str
    file: str
    branch: str


def extract(arr: list[str]):
    if size := len(arr):
        if size == 1:
            return arr[0]
    raise ValueError


class Head(Singleton):
    ref: t.Optional[Hash] = None
    loc: str = "HEAD"
    setup: bool = False

    @property
    def meta(self):
        node = extract(fs.find(self.loc, config.vcs_dir))
        data = fs.cat(path=node)
        parts = data.split(":")[-1].split("/")
        file = extract(
            fs.find(
                parts[-1:][0],
                os.path.join(config.vcs_dir, *parts[:-1]),
            )
        )
        return HeadMeta(node, file, parts[-1])

    @property
    def reflog(self):
        return fs.cat(self.meta.file).splitlines()

    def add(self, commit: Hash, dryrun: bool = False):
        if not dryrun:
            self.ref = commit
            self.ref.save(dryrun)

            entries = [commit.id] + self.reflog

            fs.touch(self.meta.file, "\n".join(entries))
            index.clear()


head = Head()


class Index(Singleton):
    loc: str = "index"
    head: Head = head

    @property
    def path(self):
        return os.path.join(config.vcs_dir, self.loc)

    @property
    def file(self):
        return fs.cat(self.path)

    @property
    def entries(self):
        return self.file.splitlines()

    @property
    def size(self):
        return len(self.entries)

    @property
    def staged(self):
        staged = {}
        all = set()

        for root, dirs, files in os.walk(config.root_dir):
            if config.is_ignored(root):
                continue
            all.add(root)
            for f in files:
                path = os.path.join(
                    root,
                    f,
                )
                if config.is_ignored(path):
                    continue
                all.add(path)

        for path in all:
            name = get_index_filename(
                path,
            )
            if entry := self._find(name):
                staged[path] = entry.group()

        return staged

    @property
    def commit_tree(self):
        return dict(
            size=sum(
                map(
                    lambda x: int(x.split("/")[2]),
                    self.staged.values(),
                )
            ),
            **self.staged,
        )

    def _locate(self, match: re.Match):
        start, end = match.span()
        match_size = end - start
        diff = start % match_size
        place = start - diff
        return int(place / match_size)

    def _find(self, name_hash: str):
        pattern = re.compile(f"^(?P<name>{name_hash}).+$", re.M)
        return pattern.search(self.file)

    @lru_cache
    def find(self, hash: Hash):
        match = self._find(hash.filename_hash)
        loc = self.size
        staged = match is not None
        changed = False
        idx = None
        if match:
            changed = match.group() != hash.index
            loc = self._locate(match)
            idx = match.group()

            return IndexSearchResult(
                loc,
                staged,
                changed,
                hash.index,
                idx,
            )

    def clear(self):
        fs.touch(self.path, "")

    def update(self, result: IndexSearchResult):
        entries = self.entries
        entries[result.loc] = result.entry
        fs.touch(self.path, "\n".join(entries))

    def remove(self, entry: str):
        folder, filename = get_object_path(entry.split("/")[-1])
        file = fs.find(filename, folder)
        if len(file):
            # print("Removing", os.path.join(folder, filename))
            fs.rm(file[0].replace(fs.root_dir, ""), True)

    def add(self, entry: str):
        entries = self.entries
        entries.append(entry)
        fs.touch(self.path, "\n".join(entries))


index = Index()


class Hash(BaseModel):
    size: int
    mode: ObjectMode
    type: str
    path: str
    content: bytes
    id: str

    @property
    def filename_hash(self):
        return get_index_filename(self.path)

    @property
    def file(self):
        return os.path.join(*get_object_path(self.id))

    @property
    def data(self):
        return self.model_dump_json()

    @property
    def index(self):
        return "/".join(
            map(
                lambda x: str(x),
                [self.filename_hash, self.type, self.size, self.id],
            )
        )

    def __str__(self):
        return str(self.data)

    def __hash__(self):
        return hash(str(self))

    def save(self, dryrun: bool = False):
        if not dryrun:
            tmp = self.file.split("/")
            folder = tmp[:-1]
            filename = tmp[-1:][0]

            try:
                if extract(
                    fs.find(filename, "/".join(folder))
                ):  # file is the same, no changes.
                    return
            except ValueError:
                pass

            fs.touch(self.file, str(self), create_dirs=True)  # create an object.

            res = index.find(self)

            if not res:
                index.add(self.index)  # add to the index.
            elif res.changed:
                if res.idx:
                    index.remove(res.idx)  # remove old entry
                index.update(res)  # update current

        return self

    @staticmethod
    def create(path: str, content: bytes, mode: ObjectMode = FILE):
        type = {FILE: "blob", DIR: "tree"}[mode]
        size = len(content)
        id = get_hash(content).hexdigest()
        return Hash(
            size=size,
            mode=mode,
            type=type,
            path=path,
            content=content,
            id=id,
        )

    @classmethod
    def _build_dir(cls, path: str, dryrun: bool):
        objects = []
        for root, dirs, files in os.walk(path):
            for f in files:
                file = os.path.join(root, f)
                if config.is_ignored(file):
                    continue

                objects.append(
                    cls._build_file(
                        file,
                        dryrun,
                    )
                )
        return objects

    @classmethod
    def _build_file(cls, path: str, dryrun: bool):
        with open(path, "rb") as fp:
            return cls.create(
                path,
                fp.read(),
                FILE,
            ).save(dryrun)

    @classmethod
    def _build(cls, path: str, *args, **kwargs):
        is_file = not os.path.isdir(path)
        if is_file:
            return cls._build_file(path, *args, **kwargs)
        return cls._build_dir(path, *args, **kwargs)

    @staticmethod
    def build(path: str, dryrun: bool = False):
        relative = os.path.join(config.root_dir, path if path != "." else "")

        if not config.is_ignored(path):
            return Hash._build(relative, dryrun)
