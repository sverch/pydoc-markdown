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


from __future__ import print_function
from collections import OrderedDict
from .base import gen_link_markup
import os


class DocumentIndex(object):
  """
  The index manages all documents and sections globally. It keeps track of
  the symbolic names allocated for the sections to be able to link to them
  from other sections.

  # Attributes
  documents (dict):
  sections (dict):
  """

  def __init__(self):
    self.documents = OrderedDict()
    self.sections = OrderedDict()

  def add_document(self, document):
    assert isinstance(document, Document), repr(document)
    if not document.filename:
      raise ValueError('Document.filename is not set')
    if document.filename in self.documents:
      raise ValueError('Document "{}" already exists'.format(document.filename))
    self.documents[document.filename] = document
    for section in document.iter_sections():
      if section.id:
        self.sections[section.id] = section

  def iter_documents(self):
    return iter(self.documents.values())

  def remove_documents(self, documents):
    for doc in documents:
      self.remove_sections(doc.sections)
    self.documents = OrderedDict(
      (k, v) for k, v in self.documents.items()
      if v not in documents
    )

  def remove_sections(self, sections):
    self.sections = {
      k: v for k, v in self.sections.items()
      if v not in sections
    }


class Document(object):
  """
  Represents a single document that may contain several #Section#s. Every
  document *must* have a relative URL associated with it.

  # Attributes

  index (Index): The index that the document belongs to.

  url (str): The relative URL of the document.
  """

  def __init__(self):
    self.index = None
    self.filename = None
    self.sections = []

  def iter_sections(self):
    return iter(self.sections)

  def add_section(self, section):
    if self.index and section.id:
      self.index.sections[section.id] = section
    section.document = self
    self.sections.append(section)

  def remove(self):
    if self.index:
      self.index.remove_documents([self])
    self.index = None

  @classmethod
  def join(cls, documents):
    result = cls()
    for doc in documents:
      for section in doc.sections:
        result.add_section(section.clone())
    return result


class Section(object):
  """
  A section represents a part of a #Document that can be linked to. It
  contains Markdown-formatted content that will be rendered into a file
  at some point.

  # Attributes

  doc (Document): The document that the section belongs to.

  identifier (str, None):
    The globally unique identifier of the section. This identifier usually
    matches the name of the element that the section describes (eg. a class
    or function) and will be used for cross-referencing.

  title (str, None):
    The title of the section. If specified, it will be rendered before
    `section.content` and the header-size will depend on the `section.depth`.

  depth (int):
    The depth of the section, defaults to 1. Currently only affects the
    header-size that is rendered for the `section.title`.

  content (str): The Markdown-formatted content of the section.
  """

  def __init__(self, id, title, depth, content):
    self.document = None
    self.id = id
    self.title = title
    self.depth = depth
    self.content = content

  def clone(self):
    return type(self)(self.id, self.title, self.depth, self.content)

  def gen_link_markup(self, title):
    """
    Returns a string that links to this section using the pydoc-markdown
    specific Markdown that will then be recognized by the indexer.
    """

    if self.id is None:
      raise RuntimeError('Section has no id')
    return gen_link_markup(title, self.id)

  def remove(self):
    if self.index:
      self.index.remove_sections([self])
    if self.document:
      self.document.sections.remove(self)
    self.document = None

  @property
  def index(self):
    if not self.document:
      return None
    return self.document.index
