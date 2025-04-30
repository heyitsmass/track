import typing as t
import pydantic as p


class IndexSearchResult(t.NamedTuple):
    loc: int
    """This entries' location in the index file."""
    staged: bool
    """If the file is staged for commit (exists in the index file)"""
    changed: bool
    """If the file has any unstaged changes."""
    entry: str
    """The entry itself."""
    idx: t.Optional[str]
    """The current index entry if it exists."""


class VCSPath(p.BaseModel):
    root: str
    description: str
    content: t.Optional[t.Any] = None
    is_file: bool = False
    is_root: bool = False
