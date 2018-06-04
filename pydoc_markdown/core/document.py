# -*- coding: utf8 -*-
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

"""
This module provides the nodal representation of a document -- which is a
rather high-level representation. It is not designed to parse any Markdown
Syntax, but only the special syntax elements for Pydoc-Markdown.

The idea is that every section can start out as a #Text node and preprocessors
can then take this node, parse its contents and split it into new nodes if a
special syntax is found (eg. into a #Text #CrossReference #Text sequence).
"""

__all__ = ['Node', 'Text', 'CrossReference', 'Section',
           'Document', 'DocumentRoot']

import weakref


class Node(object):
  """
  Base class for a node being part of a document object model.
  """

  def __init__(self):
    self._parent = None
    self._children = []

  @property
  def parent(self):
    return self._parent() if self._parent else None

  @property
  def children(self):
    return self._children

  def remove(self):
    parent = self.parent
    self._parent = None
    if parent:
      parent._children.remove(self)

  def _before_attach_to_parent(self, parent):
    pass

  def append(self, child):
    if not isinstance(child, Node):
      raise TypeError('expected Node instance, got {}'
                      .format(type(child).__name__))
    self._before_attach_to_parent(self)
    child.remove()
    child._parent = weakref.ref(self)
    self._children.append(child)

  def insert(self, index, child):
    if not isinstance(child, Node):
      raise TypeError('expected Node instance, got {}'
                      .format(type(child).__name__))
    self._before_attach_to_parent(self)
    child.remove()
    child._parent = weakref.ref(self)
    self._children.insert(index, child)

  def collapse_text(self):
    """
    Collapse multiple #Text nodes in the children of this node to one.
    """

    text = ''
    remove = []
    for child in list(self._children):
      if isinstance(child, Text):
        text += child.text
        remove.append(child)
      elif text:
        self.insert(self._children.index(child), Text(text))
        text = ''
      child.collapse_text()
    if text:
      self.append(Text(text))
    for node in remove:
      node.remove()

  def substitute(self, arg):
    """
    Substitute this node with the node or collection of nodes specified
    with *arg*.
    """

    parent = self.parent
    if not parent:
      raise RuntimeError('can not substitute() -- self has no parent')

    if isinstance(arg, Node):
      arg = [arg]
    else:
      arg = list(arg)

    for node in arg:
      if not isinstance(node, Node):
        raise TypeError('expected Node instance, got {}'
                        .format(type(node).__name__))
      node.remove()
      node._parent = weakref.ref(parent)

    index = parent._children.index(self)
    parent._children[index:index+1] = arg
    self._parent = None

  def hierarchy(self, visitor=None, filter=None, this=True):
    """
    Either returns a generator for the node's hierarchy or calls *visitor*
    for every element in that hierarchy. If *this* is #True, self will be
    yielded/visited as well.
    """

    def generator(node, this):
      if this and (not filter or filter(node)):
        yield node
      for child in node._children:
        for x in generator(child, True): yield x

    if visitor is None:
      return generator(self, this)
    else:
      for node in generator(self, this):
        visitor(node)


class Text(Node):
  """
  Represents a plain text block that will be rendered into the Markdown
  document as-is.
  """

  def __init__(self, text):
    super(Text, self).__init__()
    self.text = text

  def __repr__(self):
    text = self.text
    if len(text) > 20:
      text = text[:19] + '…'
    return 'Text(text={!r})'.format(text)

  def append(self, child):
    raise RuntimeError('Text can not have child elements.')

  def insert(self, index, child):
    raise RuntimeError('Text can not have child elements.')


class CrossReference(Node):
  """
  Represents a cross-reference to another #Section.
  """

  def __init__(self, id, label=None):
    super(CrossReference, self).__init__()
    self.id = id
    self.label = label

  def __repr__(self):
    return 'CrossReference(id={!r}, label={!r})'.format(self.id, self.label)


class Section(Node):
  """
  Represents a section in a document. This could be a namespace, class,
  function, enumeration or symbol. For all but the function type, the
  section contains additional subsections.
  """

  def __init__(self, kind, id, label=None, signature=None):
    super(Section, self).__init__()
    self.kind = kind
    self.id = id
    self.label = label
    self.signature = signature

  def __repr__(self):
    return 'Section(kind={!r}, id={!r}, label={!r})'.format(
      self.kind, self.id, self.label)

  @property
  def document(self):
    """
    Returns the #Document that this section is contained in.
    """

    parent = self.parent
    while parent:
      if isinstance(parent, Document):
        return parent
      parent = parent.parent
    return None

  @property
  def depth(self):
    """
    Returns the number of #Section parents this section has + 1.
    """

    count = 0
    while self:
      if isinstance(self, Section):
        count += 1
      self = self.parent
    return count

  def _before_attach_to_parent(self, parent):
    if not isinstance(parent, (Document, Section)):
      raise TypeError('Section can only be inserted under another Section '
                      'or Document, found {}'.format(type(parent).__name__))


class Document(Node):
  """
  Represents a document which in turn contains sections. Every document has
  a *path* that is a slash-delimited string that represents the relative
  path of the document inside the build directory (usually including the
  `.md` suffix).
  """

  def __init__(self, path):
    super(Document, self).__init__()
    self.path = path

  def __repr__(self):
    return 'Document(path={!r})'.format(self.path)


class DocumentRoot(Node):
  """
  The root node that can contain multiple documents.
  """

  def find_document(self, path, create=False):
    for child in self.children:
      if isinstance(child, Document) and child.path == path:
        return child
    if create:
      child = Document(path)
      self.append(child)
    else:
      child = None
    return child

  def find_section(self, id):
    """
    Finds the first occurence of the section with the specified *id*.
    """

    for node in self.hierarchy():
      if isinstance(node, Section) and node.id == id:
        return node
    return None

  @property
  def documents(self):
    result = []
    for child in self.children:
      if isinstance(child, Document):
        result.append(child)
    return result
