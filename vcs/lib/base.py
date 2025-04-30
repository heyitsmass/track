from __future__ import annotations

import json
import os
from datetime import datetime as dt
from datetime import timezone as tz
from pathlib import Path

from lib.abc import Singleton
from lib.config import DIR, config
from lib.fs import FileSystemTree
from lib.hash import Hash, Index, fs, index
from lib.models import VCSPath


def get_branch_paths(branch: str):
    ref_path = f"refs/heads/{branch}"
    default_branch = VCSPath(
        root=f".vcs/{ref_path}",
        description=f"The initial commit for any new project. This sets the default branch name ('{branch}').",
        is_file=True,
    )

    head_file = VCSPath(
        root=".vcs/HEAD",
        description="A text file indicating what the current working state is based on. This typically contains a symbolic reference or direct commit hash to inidicate a detatched state.",
        is_file=True,
        content=f"ref:/{ref_path}",
    )

    return default_branch, head_file


class Base(Singleton):
    setup_file_path: Path = Path("vcs/data.json").resolve()
    branch: str
    default_branch: VCSPath
    head_file: VCSPath
    fs: FileSystemTree
    index: Index
    paths: list[VCSPath]

    @classmethod
    def _init(cls):
        with open(cls.setup_file_path) as fp:
            setup_files: dict = json.load(fp)
            paths = [
                cls.default_branch,
                cls.head_file,
                *list(map(lambda x: VCSPath(**x), setup_files.get("paths", []))),
            ]
            for path in paths:
                cls._create(path)

    def __new__(cls, default_branch_name: str = "main", *args, **kwargs):
        if not cls._instance:
            cls.branch = default_branch_name
            default_branch, head_file = get_branch_paths(default_branch_name)
            cls.default_branch = default_branch
            cls.head_file = head_file
            cls.index = index
            cls.fs = fs
            if not os.path.exists(os.path.join(config.root_dir, config.vcs_dir)):
                cls._init()
        return super(Base, cls).__new__(cls, *args, **kwargs)

    @classmethod
    def _create(cls, path: VCSPath):
        if path.is_file:
            return cls._create_file(path.root, path.content)
        return cls._create_dir(path.root)

    @classmethod
    def _create_file(cls, path: str, content: str | None = None):
        cls.fs.touch(path, data=content, create_dirs=True)

    @classmethod
    def _create_dir(cls, path: str):
        cls.fs.mkdir(path, recursive=True)


class Core(Base):
    @property
    def head(self):
        return self.index.head.ref

    @property
    def reflog(self):
        return self.index.head.reflog

    @property
    def branches(self):
        names = set()

        for file in Path(
            os.path.join(config.root_dir, config.refs_dir, "heads")
        ).iterdir():
            names.add(file.name)

        return names

    def add(self, path: str, dryrun: bool = False):
        return Hash.build(path, dryrun)

    def _checkout_commit(self, id: str):
        print(id)

    def _checkout_branch(self, name: str, create: bool = False):
        if name in self.branches:
            if create:
                raise Exception(f"Branch '{name}' already exists.")
            else:
                pass

        else:
            if not create:
                raise Exception(f"Branch '{name}' doesn't exist.")
            else:
                print(self.head)
                pass

    def checkout(
        self,
        commit_id: str = None,
        branch_name: str = None,
        create_branch: bool = False,
    ):
        if not (commit_id or branch_name):
            raise Exception("Branch name or commit id is required.")
        if commit_id and create_branch:
            raise Exception("Unable to create a branch based off of a commit hash.")
        elif create_branch and not branch_name:
            raise Exception("Must provide a branch name to checkout a new branch.")

        if branch_name:
            return self._checkout_branch(branch_name, create_branch)
        return self._checkout_commit(commit_id)

    def commit(
        self,
        message: str,
        author_name: str = config.author,
        author_email: str = config.email,
        /,
        committer_name: str | None = None,
        committer_email: str | None = None,
        dryrun: bool = False,
        **kwargs,
    ):
        if self.index.size <= 0:
            return print("No changes staged for commit.")

        commit = Hash.create(
            config.root_dir,
            json.dumps(
                dict(
                    tree=self.index.commit_tree,
                    message=message,
                    timestamp=str(dt.now(tz.utc)),
                    details=dict(
                        author_name=author_name,
                        author_email=author_email,
                        committer_name=committer_name or author_name,
                        committer_email=committer_email or author_email,
                        **kwargs,
                    ),
                    parents=[self.head.id if self.head else None],
                )
            ).encode(),
            DIR,
        )

        self.index.head.add(commit, dryrun=dryrun)
