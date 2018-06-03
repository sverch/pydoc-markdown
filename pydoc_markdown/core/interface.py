# The MIT License (MIT)
#
# Copyright (c) 2018 Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

__all__ = ['IConfigurable', 'ILoader', 'IPreprocessor', 'ITextPreprocessor',
           'IRenderer']

import nr.interface

from pydoc_markdown.core.document import Text


class IConfigurable(nr.interface.Interface):

  config = nr.interface.attr(dict)


class ILoader(IConfigurable):
  """
  The #Loader interface is responsible for loading documents from a
  module spec. A module spec is any identifier followed by zero or more
  `+` characters, indicating the additional child levels of the module to
  take into account.
  """

  def load_document(self, modspec, doc):
    """
    Load a Python module from the specified *modspec* and add the contents
    to the #Document node *doc*.
    """

    raise NotImplementedError


class IPreprocessor(IConfigurable):
  """
  The #Preprocessor interface is responsible for preprocessing the plain-text
  contents and modify the document structure.
  """

  def preprocess(self, root):
    """
    Process the nodes in the #DocumentRoot node *root* and modify it.
    """

    raise NotImplementedError


class ITextPreprocessor(IPreprocessor):

  @nr.interface.default
  def preprocess(self, root):
    def recursion(node):
      if isinstance(node, Text):
        self.preprocess_text(node)
      for child in list(node.children):
        recursion(child)
    recursion(root)

  def preprocess_text(self, text_node):
    pass


class IRenderer(IConfigurable):
  """
  The renderer is ultimately responsible for rendering the Markdown documents
  to a file.
  """

  def render(self, directory, root):
    """
    Render documents to the directory.

    # Parameters
    directory (str): Path to the output directory.
    root (DocumentRoot): The collection of documents to render.
    """

  def render_document(self, fp, document):
    """
    Called to render a single document to a file. This is used in the
    Pydoc-Markdown plain mode.
    """
