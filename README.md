# Table of Contents

- [Table of Contents](#table-of-contents)
- [Repository Structure](#repository-structure)
    - [`objects/`](#objects)
    - [`refs/`](#refs)
    - [`heads/`](#heads)
    - [`HEAD`](#head)
    - [`index`](#index)
- [Content-Addressable Object Store](#content-addressable-object-store)
  - [Hashing](#hashing)
  - [Types](#types)
    - [Blob (Binary Large Object)](#blob-binary-large-object)
    - [Tree](#tree)
    - [Commit](#commit)
    - [The index / staging area](#the-index--staging-area)
- [Core Commands / User Interface](#core-commands--user-interface)
    - [`init`](#init)
    - [`add <file>`](#add-file)
    - [`commit -m <message>`](#commit--m-message)
    - [`status`](#status)
    - [`log`](#log)
    - [`checkout <branch_or_commit_hash>`](#checkout-branch_or_commit_hash)
    - [`stash`](#stash)
    - [`merge`](#merge)
- [Stash Storage](#stash-storage)
    - [`stash`](#stash-1)
    - [`stash apply`](#stash-apply)
    - [`stash pop`](#stash-pop)
    - [`stash list`](#stash-list)
- [Merging](#merging)
    - [Concept](#concept)
    - [How](#how)
  - [Implementation](#implementation)
    - [Common Ancestor](#common-ancestor)
    - [`merge <branch_name>`](#merge-branch_name)

# Repository Structure

A dedicated hidden directory within the user's project directory to store all the metadata and data.

### `objects/`

The heart of the content-addressable storage. This stores all core data objects (blobs, trees, commits).

-   Often, objects are stored in subdirectories anmed after the first two characters of their hash

-   e.g., `objects/fa/cec0ff...

-   This helps to avoid having too many files in a single directory

### `refs/`

This stores references (pointers) to specific commit hashes.

### `heads/`

Contains the files representing branches. Each file simply contains the hash of the commit that branch points to.

-   e.g., `refs/heads/main`

### `HEAD`

A text file indicating what the current working state is based on. This typically contains a symbolic reference or direct commit hash to inidicate a detatched state.

-   e.g., `ref: refs/heads/main` indicating we're on main branch

-   e.g., `facec0ffee...` indicating we're on a detatched branch

### `index`

This file acts as the staging area. It's a crucial intermediate step between the working directy and the reposity history. It lists files and their corresponding blob hashes that are staged for the _next_ commit

# Content-Addressable Object Store

## Hashing

The hash function. Everything stored in the objects directory is identified by the hash of its content. While we dont need to be cryptographically secure, we need a hash function with low collision potential.

-   SHA-3
    -   **Blake3**
-   SHA-256

We'll use Blake3 as it implements a Merkle Tree which naturally supports hash trees for storing data.

## Types

### Blob (Binary Large Object)

Represents the raw content of a file. The hash is calculated based _only_ on the file's content.

-   Using this method. When a file is added:

    -   Hash its content

    -   Create a blob object _(if it doesn't exist)_

    -   Store it in the `objects` directory named after the hash

    -   Often compressed

-   File Header `blob <size>\0`

### Tree

Represents a directory snapshot. It contains a list of entries, where each entry includes:

-   File mode

    -   e.g.,

        -   100644 for regular files

        -   040000 for subdirectories

-   Object Type (blob or tree)
-   Object Hash of the referenced blob or subtree
-   Filename

The tree object itself is then hashed based on its _formatted_ content and stored in the `objects` directory.

-   This allows us to represent directories recursively.

-   File Header `tree <size>\0`

### Commit

Represents a snapshot of the entire project at a specific point in time. It contains:

-   The hash of the root **tree** object representing the project's state for this commit.

-   The hash(es) of the **parent commit(s)**.

-   The first commit has no parent

-   Usually one parent, more for merges

-   Author name and email + timestamp

-   Committer name and email + timestamp (can be different from author).

-   Commit message.

Similar to blobs and trees, the commit object's content is formatted and then hashed to get its unique commit ID

-   File Header `commit <size>\0`

### The index / staging area

A binary mechanism used to track which ffiles from the working directory are prepared for the next commit.

This typically stores the:

-   File path

-   Hash of the corresponding **blob** object currently staged

-   File metadata to quickly check if the working directory version has changed since it was added to the index.

-   Modification time

-   Size

-   ...

# Core Commands / User Interface

### `init`

Creates the repository structure (`.vcs` directory and subdirectory/files)

```
.vcs/
	├── objects
	├── refs/
	│ ├── heads/
	│ │ └── main
	│ └── stash/
	│ └── latest
	├── HEAD
	└── index
```

### `add <file>`

1. Reads the specified file from the working directory.

2. Calculates the has of its content

    - This creates a blob object

3. Stores the blob object in `objects/` if it doesn't already exist (content-addressable!).

4. Updates the `index` file to record that this file path is now associated with this specific blob hash.

### `commit -m <message>`

1. Builds `tree` objects based on the current state of the `index`

    - Often done recursively, starting from the root directory.

    - A tree object is created for each directory represented in the index

    - Referencing the blobs (for files) and sub-trees (for subdirectories) listed in the index.

2. Creates a `commit` object containing

    - The hash of the root tree object created in step 1

    - The hash of the _current_ commit (read from `HEAD`, pointing to the current branch reference)

    - This becomes the parent commit

    - Author/commiterinfo (maybe hardcoded or read from config)

    - The provided commit message.

3. Stores the commit object in `objects/`

4. Updates the current branch reference (found via `HEAD`) in `refs/heads/` to point to the hash of the _new_ commit object.

### `status`

Compares:

1. Working directory vs `index`

    - shows changes not yet staged

2. `index` vs `HEAD` commit

    - shows changes staged for commit

### `log`

Starts from the commit hash, pointed to by `HEAD` and prints its information (message, author, date), and follows the `parent` hash to the previous commit. This repeats until the initial commit (no parent) is reached.

### `checkout <branch_or_commit_hash>`

1. Read from the specific commit object.

2. Gets the root tree hash from the commit object.

3. Recursively reads the tree(s) and associated blob objects to reconstruct the project state for that commit.

4. Updates the **working directory** files/directories to match that state (careful: this can overwrite changes!).

5. Updateds the `index` to match the checked-out state

6. Updates the `HEAD` file to point ot that specific branch or directly to the commit hash (detatched `HEAD`)

-   e.g., `ref: ref/heads/other_branch`

### `stash`

See [Stash Storage](#stash-storage)

### `merge`

See [Merging](#merging)

# Stash Storage

We need a place to store references to stash commits. In order to use a stack method and keep a single ref pointing to the _latest_ stash. We'll use a reflog `refs/stash`

### `stash`

1. Check if there's anything to stash by checking if the index and/or working directory are different from HEAD

    - If not, do nothing

2. Create an index commit

    - Build a tree from the _current index_ and creat a commit object referencing this tree.

    - The parent should be the current `HEAD` commit, we can call `1`

3. Create a working directory commit
    - Read the _current_ working directory state (considering only tracked files)
    - Create blob/tree objects for the working directory state.
    - Create a commit object `W` referencing this tree.
    - **Crucially**, make the parent _both_ the `HEAD` commit (`H`) and the index commit (`I`) created above.
        - This strcuture implicitly encodes the difference between staged and unstaged changes.
4. Record the stash
    - store the hash of the main stash commit (`W`) in `refs/stash`
    - store the `HEAD` commit hash (`H`) it was based on
5. Clean up by resetting the index and working directory to match the `HEAD` commit (like a `checkout HEAD -- .`)
    - Read the tree associated with the `HEAD` commit
    - Update the working directory files to match th eblobs referenced by that tree.
    - Update the `index` file to match that tree

### `stash apply`

1. Read the latest stash commit (`W`) hash from your stash storage.

    - Retrieve its parent(s) (`H`, and potentially `I`)

2. Merge the changes represented by the stash back into the current working directory and index.

    - Perform a 3-way merge between the base commit (`H`), the stash commit (`W`), and the _current_ `HEAD` commit

    - Apply the resulting changes to the `index` and working directory

    - Handle conflicts.

3. Handle conflicts

    - If the merge logic detects conflicts

    - e.g., the same lines changed differently in the stash and the current branch since the stash was created

    - Mark the files as conflicted (`<<<<<<<<<< =============== >>>>>>>>>>`) and let the user resolve them

    - The index should resolve these conflicts.

### `stash pop`

This is the same as `stash apply` except it _also_ removed the applied stash entry from the stash storage

### `stash list`

Reads from stash storage and siplays the available stashes

    stash@{0}: On main: <stash commit message fragment>

# Merging

### Concept

Combine the history of two different branches (or commits).

### How

-   **Common Ancestor**: Find common ancestors by determining the most recent commit that is an ancestor of both branches being merged.

-   **Fast-Forward**: If the current branch's tip is a direct ancestor of the other branch's tip, move the current branch pointer forward.

    -   No new commit is created

-   **Three-Way-Merge**: If the branches have diverged, Compare the file trees of the common ancestor, current branch tip (`HEAD`), and the other branch tip (`branch`) and attempt to combine the changes.

-   **Merge Commit**: If the three-way merge is successful (or after conflicts are resolved); Create a new **merge commit**. This commit has two parents: the `HEAD` commit and the tip commit of the branch that was merged in.

    -   The resulting tree represents the result of this merge.

## Implementation

### Common Ancestor

Utilize a function that takes two commit hashes and traverses the commit graph (following parent pointers) backwards from both commits until a common hash is found.

-   Breadth-First Search or careful Depth-First-Search

### `merge <branch_name>`

1. Resolve `<branch_name>` to its corresponding commit hash (`theirs`). Get the current `HEAD` commit (`ours`).

2. Find the common ancestor commit hash (`base`) using the algorithm above.

3. **Check for Fast-Forward** (if `base` is the same as `ours`, then `ours` is a direct ancestor of `theirs`)

    - Update the current branch reference (in `refs/heads/`) to point to `theirs`

    - Update the working directory and index to match the three of `theirs` (like `checkout`)

    - Report "Fast-forward merge" and exit.

4. **Check for Already up-to-date**

    - If `base` is the same as `theirs` or if `ours` equals `theirs`, the changes are already included.

    - Report "Already up-to-date" and exit.

5. **Perform Three-Way-Merge**

    - Get the root tree objects for `base`, `ours`, and `theirs`

    - Implement a recursive tree-merging function:

        - Compare entries (files/subdirs) present in `base`, `ours`, and `theirs`.

        - **Files**:

            - If changed in ours only (vs base), keep ours version.

            - If changed in theirs only, take theirs version.

            - If changed in both:

            - If changes are identical, take the changed version.

            - If changes are different -> CONFLICT.

            - If deleted in one and modified in the other -> CONFLICT.

            - If deleted in both -> delete it.

        - **Handle Added Files**

            - If added in `ours` or `theirs` (check if present in `base`)

            - If added in both with different content -> **CONFLICT**

        - **Recursively Merge Subtrees**

        - **Build Merged Index/Working Directory**

            - While merging

                - Update the working directory and build a representation fo the merged state

                    - potentially directly into the `index`

        - **Conflict Handling**

            - If conflicts occur:

                - Write conflict markers (`<<<<<<< HEAD, =======, >>>>>>> <branch_name>`) into the affected files in the working directory.

                - Update `inde to mark these files are unmerged

                    - Can use multiples stages of the index for this

                    - Simpler way maybe a special flag or storing multiple blob hashes per conflicting path

                - Report conflicts and exit. The user must resolve them manually and run `commit`

6. **Create Merge Commit (No Conflicts)**

    - Build the final merged tree object from the successful merge result

        - Or the resolved state reflected in the index if conflicts were handles manually in prior step

    - Create a new commit object

        - Tree: hash of the merged tree

        - Parents: _Two_ hashes - `ours` and `theirs`

        - Author/Committer: Standard info

        - Message: Generate a default message like `Merge branch '<branch_name>'`

-   Store the new commit object.

-   Update the current branch reference in `refs/heads/` to point to this new merge commit hash.

-   (The working directory and index should already reflect the merged state from state 5)
