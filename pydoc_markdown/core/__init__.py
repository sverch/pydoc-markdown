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
from .document import *
from .interface import *
from ..utils.imputils import import_object_with_scope
from ..utils.pydoc import dir_object, get_docstring, get_function_signature, trim

import inspect
import nr.interface
import re


class PythonLoader(nr.interface.Implementation):
  """
  Expects absolute identifiers to import with #import_object_with_scope().
  """

  nr.interface.implements(ILoader)

  def load_document(self, modspec, doc):
    levels, modspec = len(modspec), modspec.rstrip('+')
    levels -= len(modspec)
    self._build_document(doc, modspec, levels+1)

  def _load_section(self, ident, depth):
    obj, scope = import_object_with_scope(ident)

    if '.' in ident:
      default_title = ident.rsplit('.', 1)[1]
    else:
      default_title = ident

    title = getattr(obj, '__name__', default_title)
    if inspect.isfunction(title):
      title += '()'

    if inspect.isclass(obj):
      kind = 'class'
    elif isinstance(obj, (classmethod, staticmethod, property)):
      kind = type(obj).__name__
    else:
      kind = type(obj).__name__

    section = Section(kind, ident, title)
    section.append(Text(trim(get_docstring(obj))))

    # Add the function signature in a code-block.
    if callable(obj):
      section.signature = get_function_signature(
        obj, scope if inspect.isclass(scope) else None)

    section._loader_context = {'obj': obj, 'scope': scope}
    return section

  def _build_document(self, parent, ident, max_depth, depth=1):
    if depth > max_depth:
      return

    try:
      section = self._load_section(ident, depth)
    except Exception:
      print('Error while loading "{}"'.format(ident))
      raise

    parent.append(section)

    sort_order = getattr(self.config, 'sorting', 'line')
    need_docstring = getattr(self.config, 'filter', ['docstring'])
    for sub in dir_object(section._loader_context['obj'], sort_order, need_docstring):
      sub = ident + '.' + sub
      self._build_document(section, sub, max_depth, depth+1)


class CompoundPreproc(nr.interface.Implementation):
  nr.interface.implements(IPreprocessor)

  def __init__(self, *preprocessors):
    self._config = None
    self.preprocessors = list(preprocessors)
    if not all(IPreprocessor.implemented_by(x) for x in self.preprocessors):
      raise TypeError('must implement IPreprocessor interface.')

  def add(self, preproc):
    assert IPreprocessor.implemented_by(preproc)
    self.preprocessors.append(preproc)

  @property
  def config(self):
    return self._config

  @config.setter
  def config(self, config):
    self._config = config
    for preproc in self.preprocessors:
      preproc.config = config

  @nr.interface.override
  def preprocess(self, root):
    for preproc in self.preprocessors:
      preproc.preprocess(root)



class PdmPreproc(nr.interface.Implementation):
  """
  This class implements the basic Pydoc-Markdown preprocessor.

  Markdown headers are always converted to bold markup in the output Markdown.
  Some special headers enable a different formatting behaviour. Namely, these
  headers are "Arguments", "Parameters", "Attributes", "Members", "Raises"
  and "Returns".

  Example 1:

      # Parameters
      a (int): An integer.
      return (int): Another integer.
      raises (ValueError): If something bad happens.

  Example 2:

      # Parameters
      a (int): An integer.

      # Returns
      int: Another integer.

      # Raises
      ValueError: If something bad happens.
  """

  nr.interface.implements(ITextPreprocessor)

  def preprocess_text(self, node):
    """
    Preprocess the contents of *section*.
    """

    nodes = []
    codeblock_opened = False
    current_section = None
    for line in node.text.split('\n'):
      line += '\n'
      if line.startswith("```"):
        codeblock_opened = (not codeblock_opened)
      if codeblock_opened:
        nodes.append(Text(line))
      else:
        current_section = self._preprocess_line(line, current_section, nodes)

    node.substitute(nodes)
    for node in nodes:
      if isinstance(node, Text):
        new_nodes = []
        self._preprocess_refs(node.text, new_nodes)
        node.substitute(new_nodes)

  def _preprocess_line(self, line, current_section, nodes):
    match = re.match(r'# (.*)$', line)
    if match:
      current_section = match.group(1).strip().lower()
      line = re.sub(r'# (.*)$', r'__\1__\n', line)

    # TODO: Parse type names in parentheses after the argument/attribute name.
    if current_section in ('arguments', 'parameters'):
      style = r'- __\1__:\3'
    elif current_section in ('attributes', 'members', 'raises'):
      style = r'- `\1`:\3'
    elif current_section in ('returns',):
      style = r'`\1`:\3'
    else:
      style = None
    if style:
      #                  | ident  | types     | doc
      line = re.sub(r'\s*([^\\:]+)(\s*\(.+\))?:(.*)$', style, line)

    nodes.append(Text(line))
    return current_section

  def _preprocess_refs(self, content, nodes):
    expr = re.compile('(?P<prefix>^| |\t)#(?P<ref>[\w\d\._]+)(?P<parens>\(\))?')
    index = 0
    while True:
      match = expr.match(content, index)
      if not match:
        nodes.append(Text(content[index:]))
        break

      ref = match.group('ref')
      parens = match.group('parens') or ''
      has_trailing_dot = False
      if not parens and ref.endswith('.'):
        ref = ref[:-1]
        has_trailing_dot = True

      if match.group('prefix'):
        nodes.append(Text(match.group('prefix')))
      nodes.append(CrossReference(ref, '{}{}'.format(ref, parens)))
      if has_trailing_dot:
        nodes.append(Text('.'))


class SphinxPreproc(nr.interface.Implementation):
  nr.interface.implements(IPreprocessor)

  @nr.interface.override
  def preprocess(self, root):
    pass # TODO


class Renderer(nr.interface.Implementation):
  """
  The default renderer implementation.
  """

  nr.interface.implements(IRenderer)

  @nr.interface.override
  def render(self, directory, root):
    for document in root.documents:
      with open(os.path.join(directory, doc.path + '.md'), 'w') as fp:
        self.render_node(fp, document)

  @nr.interface.override
  def render_document(self, fp, doc):
    self.render_node(fp, doc)

  def render_node(self, fp, node):
    if isinstance(node, Document):
      for child in node.children:
        self.render_node(fp, child)
    elif isinstance(node, Section):
      print(
        '<h{depth} id="{id}"><small>{kind}</small> {title}</h{depth}>\n'.format(
          kind=node.kind,
          depth=node.depth,
          id=node.id,
          title=node.label
        ),
        file=fp
      )
      if node.signature:
        fp.write('> `{}`\n\n'.format(node.signature))
      for child in node.children:
        self.render_node(fp, child)
    elif isinstance(node, Text):
      fp.write(node.text)
    elif isinstance(node, CrossReference):
      # TODO: Actually generate links to other documents.
      fp.write('`{}`'.format(node.label or node.id))
    else:
      print('warning: unexpected node in Renderer.render_node(): {}'.format(node))
