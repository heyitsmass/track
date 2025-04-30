import typing as t
import os
import shutil
import json


class TreeNode:
    """
    A node in an n-ary tree representing a file or directory in a file system.
    """

    def __init__(self, name: str, is_file: bool = False, data: t.Any = None):
        """
        Initialize a TreeNode.

        Args:
            name (str): Name of the file or directory
            is_file (bool): True if this node represents a file, False if it's a directory
            data (any): Optional data associated with this node
        """
        self.name: str = name
        self.is_file: bool = is_file
        self.data: t.Any = data
        self.children: t.Dict[
            str, "TreeNode"
        ] = {}  # Dictionary mapping child names to child nodes
        self.parent: t.Optional["TreeNode"] = None  # Reference to parent node

    def add_child(self, child_node: "TreeNode"):
        """
        Add a child node to this node.

        Args:
            child_node (TreeNode): The child node to add

        Returns:
            TreeNode: The added child node
        """
        self.children[child_node.name] = child_node
        child_node.parent = self
        return child_node

    def get_child(self, name: str):
        """
        Get a child node by name.

        Args:
            name (str): Name of the child node

        Returns:
            TreeNode or None: The child node if found, None otherwise
        """
        return self.children.get(name)

    def remove_child(self, name: str):
        """
        Remove a child node by name.

        Args:
            name (str): Name of the child node to remove

        Returns:
            TreeNode or None: The removed child node if found, None otherwise
        """
        if name in self.children:
            child = self.children[name]
            child.parent = None
            del self.children[name]
            return child
        return None

    def get_path(self) -> str:
        """
        Get the full path from the root to this node.

        Returns:
            str: The full path as a string
        """
        if self.parent is None:
            return self.name
        return os.path.join(self.parent.get_path(), self.name)

    def __str__(self):
        """String representation of the node."""
        node_type = "File" if self.is_file else "Directory"
        return f"{node_type}: {self.name}"


class FileSystemTree:
    """
    An n-ary tree representing a file system structure.
    """

    _fs: t.Optional["FileSystemTree"] = None

    def __new__(cls, *args, **kwargs):
        if not cls._fs:
            cls._fs = super(FileSystemTree, cls).__new__(cls)

        return cls._fs

    def __init__(self, root_name: t.Optional[str] = None):
        """
        Initialize the file system tree with a root directory.

        Args:
            root_name (str): Name of the root directory
        """
        if root_name and not os.path.exists(root_name):
            os.makedirs(root_name)

        self.root_dir = root_name if root_name else os.getcwd()
        self.root: TreeNode = TreeNode(self.root_dir, is_file=False)
        self.current_node: TreeNode = self.root
        # Initialize the tree from the existing file system
        if os.path.exists(self.root_dir):
            self._build_tree_from_fs(self.root_dir, self.root)

    def _is_text_file(self, filepath):
        return not os.path.isdir(filepath)

    def _build_tree_from_fs(self, path, node):
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            is_file = os.path.isfile(item_path)

            child_node = TreeNode(item, is_file=is_file)
            node.add_child(child_node)

            if is_file:
                # For small text files, we can load the content
                if (
                    self._is_text_file(item_path)
                    and os.path.getsize(item_path) < 1024 * 1024
                ):  # 1MB limit
                    try:
                        with open(item_path, "rb") as f:
                            child_node.data = f.read()
                    except FileNotFoundError:
                        pass
            else:
                # Recursively build tree for directories
                self._build_tree_from_fs(item_path, child_node)

    def _get_fs_path(self, path: str):
        # print(path)
        if path.startswith("/"):
            node_path = path[1:]  # Remove leading '/'
            return node_path  # os.path.join(self.root_dir, node_path)
        else:
            node = self._get_node_at_path(path)
            if node is None:
                return path

            rel_path = node.get_path()
            return rel_path
            if rel_path == self.root_dir:
                return rel_path
            return os.path.join(self.root_dir, rel_path)

    def mkdir(self, path, recursive=False):
        """
        Create a directory at the specified path.

        Args:
            path (str): Path where to create the directory
            recursive (bool): If True, create parent directories as needed

        Returns:
            TreeNode: The created directory node

        Raises:
            ValueError: If the path is invalid or if a file exists at the path
        """
        if recursive:
            node = self._mkdir_recursive(path)
        else:
            parent_node, node_name = self._get_parent_node_and_name(path)
            if parent_node is None:
                raise Exception(f"Unable to locate parent node for '{path}'")

            if node_name in parent_node.children:
                if parent_node.children[node_name].is_file:
                    raise ValueError(
                        f"Cannot create directory '{node_name}': A file with that name already exists"
                    )
                node = parent_node.children[node_name]
            else:
                node = TreeNode(node_name, is_file=False)
                parent_node.add_child(node)

            # Create actual directory on the filesystem
            fs_path = self._get_fs_path(node.get_path())
            if not os.path.exists(fs_path):
                os.makedirs(fs_path)

            return node

    def _mkdir_recursive(self, path):
        """
        Recursively create a directory and all its parent directories.

        Args:
            path (str): Path to create

        Returns:
            TreeNode: The created directory node
        """
        # Handle absolute paths
        if path.startswith("/"):
            current = self.root
            path = path[1:]
        else:
            current = self.current_node

        if not path:
            return current

        parts = path.split("/")
        for part in parts:
            if part == "" or part == ".":
                continue
            elif part == "..":
                if current.parent:
                    current = current.parent
            else:
                if part in current.children:
                    if current.children[part].is_file:
                        raise ValueError(
                            f"Cannot create directory '{part}': A file with that name already exists"
                        )
                    current = current.children[part]
                else:
                    new_node = TreeNode(part, is_file=False)
                    current.add_child(new_node)
                    current = new_node

                    # Create the actual directory
                    fs_path = self._get_fs_path(current.get_path())
                    if not os.path.exists(fs_path):
                        os.makedirs(fs_path)

        return current

    def touch(self, path, data=None, create_dirs=False):
        """
        Create a file at the specified path.

        Args:
            path (str): Path where to create the file
            data (any): Optional data to store in the file
            create_dirs (bool): If True, create parent directories as needed

        Returns:
            TreeNode: The created file node

        Raises:
            ValueError: If the path is invalid or if a directory exists at the path
        """
        # print(path, data, create_dirs)
        if create_dirs:
            node = self._touch_with_dirs(path, data)
        else:
            parent_node, node_name = self._get_parent_node_and_name(path)
            if parent_node is None:
                raise Exception(f"Unable to locate parent node for '{path}'")

            if node_name in parent_node.children:
                if not parent_node.children[node_name].is_file:
                    raise ValueError(
                        f"Cannot create file '{node_name}': A directory with that name already exists"
                    )
                node = parent_node.children[node_name]
                node.data = data
            else:
                node = TreeNode(node_name, is_file=True, data=data)
                parent_node.add_child(node)

        # Create or update the actual file
        fs_path = self._get_fs_path(node.get_path())
        with open(fs_path, "w", encoding="utf-8") as f:
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))

        return node

    def _touch_with_dirs(self, path, data=None):
        """
        Create a file and all necessary parent directories.

        Args:
            path (str): Path where to create the file
            data (any): Optional data to store in the file

        Returns:
            TreeNode: The created file node

        Raises:
            ValueError: If part of the path conflicts with an existing file
        """
        if "/" not in path:
            return self.touch(path, data)

        parent_path, file_name = path.rsplit("/", 1)
        parent_dir = self._mkdir_recursive(parent_path)

        if file_name in parent_dir.children:
            if not parent_dir.children[file_name].is_file:
                raise ValueError(
                    f"Cannot create file '{file_name}': A directory with that name already exists"
                )
            node = parent_dir.children[file_name]
            node.data = data
        else:
            node = TreeNode(file_name, is_file=True, data=data)
            parent_dir.add_child(node)

        # Create or update the actual file
        fs_path = self._get_fs_path(node.get_path())
        with open(fs_path, "w", encoding="utf-8") as f:
            if data is not None:
                if isinstance(data, dict) or isinstance(data, list):
                    json.dump(data, f, indent=2)
                else:
                    f.write(str(data))

        return node

    def cd(self, path: str):
        """
        Change the current directory to the specified path.

        Args:
            path (str): Path to change to

        Returns:
            TreeNode: The new current node

        Raises:
            ValueError: If the path is invalid or points to a file
        """
        if path == "/":
            self.current_node = self.root
            return self.current_node

        target_node = self._get_node_at_path(path)

        if target_node is None:
            raise ValueError(f"No such directory: {path}")

        if target_node.is_file:
            raise ValueError(f"Not a directory: {path}")

        self.current_node = target_node
        return self.current_node

    def ls(self, path: t.Optional[str] = None):
        """
        List contents of a directory.

        Args:
            path (str, optional): Path to list. If None, list current directory.

        Returns:
            dict: Dictionary mapping names to nodes in the directory

        Raises:
            ValueError: If the path is invalid or points to a file
        """
        if path is None:
            return self.current_node.children

        target_node = self._get_node_at_path(path)

        if target_node is None:
            raise ValueError(f"No such directory: {path}")

        if target_node.is_file:
            raise ValueError(f"Not a directory: {path}")

        return target_node.children

    # @lru_cache
    def cat(self, path: str) -> str:
        """
        Get the data stored in a file.

        Args:
            path (str): Path to the file

        Returns:
            any: The data stored in the file

        Raises:
            ValueError: If the path is invalid or points to a directory
        """
        target_node = self._get_node_at_path(path)

        if target_node is None:
            raise ValueError(f"No such file: {path}")

        if not target_node.is_file:
            raise ValueError(f"Not a file: {path}")

        # If the data is not already loaded in memory, read from file
        if target_node.data is None:
            fs_path = self._get_fs_path(target_node.get_path())
            try:
                with open(fs_path, "r", encoding="utf-8") as f:
                    target_node.data = f.read()
            except UnicodeDecodeError:
                return "[Binary file content not displayed]"
            except Exception as e:
                return f"[Error reading file: {str(e)}]"
        if isinstance(target_node.data, bytes):
            return target_node.data.decode()

        return str(target_node.data)

    def rm(self, path, recursive=False):
        """
        Remove a file or directory.

        Args:
            path (str): Path to the file or directory to remove
            recursive (bool): If True, remove directories even if not empty

        Returns:
            TreeNode: The removed node

        Raises:
            ValueError: If the path is invalid or if trying to remove a non-empty directory without recursive flag
        """
        parent_node, node_name = self._get_parent_node_and_name(path)
        if parent_node is None:
            raise Exception(f"Unable to locate parent node for '{path}'")

        if node_name not in parent_node.children:
            raise ValueError(f"No such file or directory: {path}")

        node = parent_node.children[node_name]

        if not node.is_file and node.children and not recursive:
            raise ValueError(
                f"Cannot remove directory '{node_name}': Directory not empty. Use recursive=True to force removal."
            )

        # Remove from the actual file system
        fs_path = self._get_fs_path(node.get_path())
        try:
            if os.path.exists(fs_path):
                if node.is_file:
                    os.remove(fs_path)
                else:
                    shutil.rmtree(fs_path)
        except Exception as e:
            raise ValueError(f"Error removing {fs_path}: {str(e)}")

        # Then remove from our tree
        return parent_node.remove_child(node_name)

    def find(self, name: str, start_path: t.Optional[str] = None) -> t.List[str]:
        """
        Find nodes with the given name.

        Args:
            name (str): Name to search for
            start_path (str, optional): Path to start the search from. If None, start from root.

        Returns:
            list: List of paths to nodes with the given name
        """
        if start_path is None:
            start_node = self.root
        else:
            start_node = self._get_node_at_path(start_path)
            if start_node is None:
                raise ValueError(f"No such directory: {start_path}")

        results: list[str] = []
        self._find_recursive(start_node, name, results)

        return list(map(lambda x: x.lstrip(self.root_dir + "/"), results))

    def _find_recursive(self, node: TreeNode, name: str, results: t.List[str]):
        """
        Recursively search for nodes with the given name.

        Args:
            node (TreeNode): Current node to search
            name (str): Name to search for
            results (list): List to store the results
        """
        if node.name == name:
            results.append(node.get_path())

        for child in node.children.values():
            self._find_recursive(child, name, results)

    def exists(self, path: str):
        """
        Check if a file or directory exists at the specified path.

        Args:
            path (str): Path to check

        Returns:
            bool: True if a node exists at the path, False otherwise
        """
        return self._get_node_at_path(path) is not None

    def is_file(self, path: str):
        """
        Check if a path points to a file.

        Args:
            path (str): Path to check

        Returns:
            bool: True if the path points to a file, False otherwise
        """
        node = self._get_node_at_path(path)
        return node is not None and node.is_file

    def is_dir(self, path: str):
        """
        Check if a path points to a directory.

        Args:
            path (str): Path to check

        Returns:
            bool: True if the path points to a directory, False otherwise
        """
        node = self._get_node_at_path(path)
        return node is not None and not node.is_file

    def _get_node_at_path(self, path: str) -> t.Union[TreeNode, None]:
        """
        Get the node at the specified path.

        Args:
            path (str): Path to the node

        Returns:
            TreeNode or None: The node at the path if it exists, None otherwise
        """
        # Handle absolute paths

        if path.startswith("/"):
            current = self.root
            path = path[1:]
        else:
            current = self.current_node

        if not path:
            return current

        if path == "..":
            return current.parent if current.parent else current

        if path == ".":
            return current

        parts = path.split("/")
        for part in parts:
            if part == "":
                continue
            elif part == "..":
                if current.parent:
                    current = current.parent
            elif part == ".":
                continue
            else:
                if part in current.children:
                    current = current.children[part]
                else:
                    return None

        return current

    def _get_parent_node_and_name(
        self, path: str
    ) -> t.Tuple[t.Union[None, TreeNode], str]:
        """
        Get the parent node and name of the last component in the path.

        Args:
            path (str): Path to parse

        Returns:
            tuple: (parent_node, node_name)

        Raises:
            ValueError: If the parent directory doesn't exist
        """
        parent_path = None
        # Handle special cases
        if path == "/" or path == "":
            return parent_path, self.root.name

        # Find the last separator
        if "/" in path:
            parent_path, node_name = path.rsplit("/", 1)

            # Handle absolute paths that start with /
            if path.startswith("/") and parent_path == "":
                parent_node = self.root
            else:
                parent_node = self._get_node_at_path(parent_path)
        else:
            parent_node = self.current_node
            node_name = path

        if parent_node is None:
            raise ValueError(f"Parent directory does not exist: {parent_path}")

        return parent_node, node_name

    def print_tree(self, start_node: t.Optional[TreeNode] = None, indent=""):
        """
        Print the tree structure.

        Args:
            start_node (TreeNode, optional): Node to start printing from. If None, start from root.
            indent (str): Indentation for the current level
        """
        if start_node is None:
            start_node = self.root

        node_type = "📄" if start_node.is_file else "📁"
        print(f"{indent}{node_type} {start_node.name}")

        for child in sorted(
            start_node.children.values(), key=lambda x: (x.is_file, x.name)
        ):
            self.print_tree(child, indent + "  ")

    def sync_from_fs(self):
        self.root.children = {}
        self._build_tree_from_fs(self.root_dir, self.root)


# Example usage
if __name__ == "__main__":
    import tempfile

    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Creating file system in temporary directory: {temp_dir}")

        # Initialize the file system with the temp directory as root
        fs = FileSystemTree(temp_dir)

        # Create directories and files
        fs.mkdir("/projects", recursive=True)
        fs.touch(
            "/projects/README.md",
            "# Projects Directory\n\nThis directory contains all projects.",
        )

        # Create a nested directory structure with files
        fs.touch("/projects/python/main.py", "print('Hello, World!')", create_dirs=True)
        fs.touch(
            "/projects/python/data.json",
            {"name": "Test Data", "values": [1, 2, 3]},
            create_dirs=True,
        )

        # Create another branch of directories
        fs.touch("/documents/notes.txt", "Important notes go here", create_dirs=True)

        # Print the tree structure
        print("\nFile System Structure:")
        fs.print_tree()

        # List the actual files created in the temp directory
        print("\nActual files created:")
        for root, dirs, files in os.walk(temp_dir):
            level = root.replace(temp_dir, "").count(os.sep)
            indent = " " * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            sub_indent = " " * 2 * (level + 1)
            for file in files:
                print(f"{sub_indent}{file}")

        # Test reading a file
        print("\nContent of main.py:", fs.cat("/projects/python/main.py"))

        # Test removing a directory and verify it's gone from the file system
        fs.rm("/projects/python", recursive=True)
        print("\nAfter removing /projects/python:")
        fs.print_tree()

        # Verify the directory was actually removed from the file system
        python_dir = os.path.join(temp_dir, "projects", "python")
        print(f"\nDoes {python_dir} exist? {os.path.exists(python_dir)}")
