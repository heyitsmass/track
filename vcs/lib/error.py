import os
import pathlib as p
import typing as t
from functools import wraps


class EmptyProjectError(Exception):
    def __str__(self):
        return "Empty project. No files to process."

    @staticmethod
    def raise_on_non_existant(path: t.Union[str, p.Path]):
        if not os.path.isdir(path):
            raise EmptyProjectError


def ignore_if_non_existant(func):
    @wraps(func)
    def wrapper(path: t.Union[str, p.Path]):
        try:
            EmptyProjectError.raise_on_non_existant(path)
            return func(path)
        except EmptyProjectError:
            print(f"Ignoring non-existant directory '{str(path)}'")
            pass

    return wrapper


class IgnoredFileError(Exception):
    def __str__(self):
        return f"'{self.args[0]}' is an ignored file."


class AlreadyInitializedError(Exception):
    def __str__(self):
        return "This repo has already been initialized."


class UnstagedFilesError(Exception):
    def __str__(self):
        return "There are unsaved changes not saved for commit."
