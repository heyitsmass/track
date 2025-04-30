import os
import re
import typing as t
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings
from typing_extensions import Self


class Config(BaseSettings):
    root_dir: str = "project"
    objects_dir: str = ".vcs/objects"
    refs_dir: str = ".vcs/refs"
    heads_dir: str = ".vcs/refs/heads"
    vcs_dir: str = ".vcs"
    ignore_file: str = ".vcsignore"
    ignored_files: t.List[str] = [".vcsignore", ".vcs"]

    author: str = "anon"
    email: str = "anon@email.com"

    @model_validator(mode="after")
    def parse_ignore_file(self) -> Self:
        path = f"{self.root_dir}/{self.ignore_file}"
        if os.path.exists(path):
            with open(path, "r") as fp:
                self.ignored_files = self.ignored_files + list(
                    set(
                        map(
                            lambda x: re.sub(r"\n$|^\s|\s$", "", x),
                            fp.readlines(),
                        )
                    )
                )
        return self

    def is_ignored(self, file: str):
        files = [
            os.path.join(
                self.root_dir,
                self.vcs_dir,
                "**",
            ),
            *map(
                lambda x: os.path.join(self.root_dir, x),
                self.ignored_files,
            ),  # extend file paths
            *map(
                lambda x: os.path.join(self.root_dir, x, "**"),
                filter(lambda x: "." not in x, self.ignored_files),
            ),  # extend folder paths
        ] + self.ignored_files

        path = Path(file)

        for f in files:
            if (
                path.full_match(f)
                or path.match(f)
                or path.full_match(os.path.join(f, "**"))
            ):
                return True

        return False


DIR = "040000"
FILE = "100644"

config = Config()
