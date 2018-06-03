# Pydoc-Markdown

Pydoc-Markdown generates Python API documentation in Markdown format. It
provides a new documentation syntax while also supporting a subset of the
Sphinx documentation format.

```
usage: pydoc-markdown [-h] [--plain] [--builddir BUILDDIR] [--config CONFIG]
                      [modules [modules ...]]
```

__Table of Contents__

* [Installation](#installation)
* [Usage](#usage)
  * [Configuration](#configuration)
  * [Documentation Syntax](#documentation-syntax)
  * [Cross-references](#cross-references)
  * [Function and Class documentation](#function-and-class-documentation)
  * [Code Blocks](#code-blocks)

---

## Installation

To install the latest release from Pip:

    pip install pydoc-markdown

To get the latest development version, use:

    pip install git+https://github.com/NiklasRosenstein/pydoc-markdown.git -b develop

---

## Usage

### Configuration

Pydoc-Markdown is configured by creating a `pydoc-markdown.conf.py` file in
your current working directory. Below is an example configuration file that
also displays the default values (where applicable).

```python
modules = [
  'mymodule+',
  'mymodule.bar+,mymodule.bar.SomeClass+'
  ('testing.md', 'mymodule.testing++')  # Explicitly specify the document filename
]

bulddir = 'build/pydoc-markdown'
preprocessor = 'pydoc_markdown.core.python.Preprocessor'
loader = 'pydoc_markdown.core.python.PythonLoader'
renderer = 'pydoc_markdown.core.base.Renderer'
```

### Documentation Syntax

Pydoc-Markdown uses its own documentation syntax for creating cross-references.
Support for Sphinx syntax is planned (see [#1]).

  [#1]: https://github.com/NiklasRosenstein/pydoc-markdown/issues/1

#### Cross-references

Cross-references are specified in the format `#ID`, `#ID~text`, `#~ID` or
`#ID#suffix`. The `ID` usually will be a Python function, class or module
name. The ID may contain attribute lookups and trailing call parentheses
"`()`". For absolute references, prefix the `ID` with two
double-colons. Examples:

* `#SomeClass.member_method()`
* `#SomeClass.member_method~some_method()`
* `#~SomeClass.member_method()`
* `#~::mymodule.SomeClass.member_method()`

#### Function and Class documentation

Function arguments, members, return types and exception information can be
documented in special Markdown titles. The rendering of the content following
these titles depends on the title itself. Available special titles are:

* `# Members`, `# Attributes` (1)
* `# Parameters`, `# Arguments` (1)
* `# Returns` (2)
* `# Raises` (2)

For function documentations, the exception and return type information can
be placed in the same block as the parameters.

Example 1:

    # Parameters
    a (int): Some integer.
    return (int): Another integer
    raise (ValueError): When something bad happens.

Example 2:

    # Paramters
    a (int): Some integer.

    # Returns
    int: Another integer.

    # Raises
    ValueError: When something bad happens.

_Formal specification_:

(1): Lines beginning with `<ident> [(<type>[, ...])]:` are treated as
argument/parameter or attribute/member declarations. Types listed inside the
parenthesis (optional) are cross-linked, if possible. For attribute/member
declarations, the identifier is typed in a monospace font.

(2): Lines beginning with `<type>[, ...]:` are treated as raise/return type
declarations and the type names are cross-linked, if possible.

Lines following a name's description are considered part of the most recent
documentation unless separated by another declaration or an empty line. `<type>`
placeholders can also be tuples in the form `(<type>[, ...])`.

#### Code Blocks

GitHub-style Markdown code-blocks with language annotations can be used.

    ```python
    >>> for i in range(100):
    ...
    ```

---

<p align="center">Copyright &copy; 2018 Niklas Rosenstein</p>
