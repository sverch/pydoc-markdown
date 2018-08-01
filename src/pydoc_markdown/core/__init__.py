# -*- coding: utf8 -*-
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

__all__ = [
  'PythonLoader',
  'GroupPreprocessor',
  'PydocMarkdownPreprocessor',
  'SphinxMarkdownPreprocessor',
]


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
    if not inspect.isclass(obj) and callable(obj):
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


class GroupPreprocessor(nr.interface.Implementation):
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


class PydocMarkdownPreprocessor(nr.interface.Implementation):
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

  # Options

  pdm_reorganize (bool):
    Reorganizes the sections in the document so they are grouped for module
    level data members, functions and classes. (#True by default)
  """

  nr.interface.implements(ITextPreprocessor)

  def preprocess(self, root):
    ITextPreprocessor.preprocess(self, root)
    if getattr(self.config, 'pdm_reorganize', True):
      for doc in root.documents:
        for module in (x for x in doc.children if x.kind == 'module'):
          self._reorganize_module(module)

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
    expr = re.compile('(?P<prefix>^| |\t)#(?P<ref>[\w\d\._]+)(?P<parens>\(\))?', re.M)
    index = 0
    while True:
      match = expr.search(content, index)
      if not match:
        nodes.append(Text(content[index:]))
        break

      ref = match.group('ref')
      parens = match.group('parens') or ''
      has_trailing_dot = False
      if not parens and ref.endswith('.'):
        ref = ref[:-1]
        has_trailing_dot = True

      if match.start() > index:
        nodes.append(Text(content[index:match.start()]))
      if match.group('prefix'):
        nodes.append(Text(match.group('prefix')))
      nodes.append(CrossReference(ref, '{}{}'.format(ref, parens)))
      if has_trailing_dot:
        nodes.append(Text('.'))

      index = match.end()

  def _reorganize_module(self, module):
    assert isinstance(module, Section)
    classes = []
    functions = []
    other = []
    for section in list(module.children):
      if not isinstance(section, Section): continue
      if section.kind == 'class': classes.append(section)
      elif section.kind == 'function': functions.append(section)
      else: other.append(section)
      section.remove()

    if other:
      section = Section(None, 'data-members', 'Data Members')
      [section.append(x) for x in other]
      module.append(section)
    if functions:
      section = Section(None, 'functions', 'Functions')
      [section.append(x) for x in functions]
      module.append(section)
    if classes:
      section = Section(None, 'classes', 'Classes')
      [section.append(x) for x in classes]
      module.append(section)


class SphinxMarkdownPreprocessor(nr.interface.Implementation):
  nr.interface.implements(ITextPreprocessor)

  @nr.interface.override
  def preprocess_text(self, node):
    nodes = []  # A list of nodes that act as a substitute.
    in_codeblock = False
    keyword = None
    components = {}

    for line in node.text.split('\n'):
      if line.startswith("```"):
        in_codeblock = not in_codeblock

      if not in_codeblock:
        match = re.match(r':(?:param|parameter)\s+(\w+)\s*:(.*)?$', line)
        if match:
          keyword = 'Arguments'
          param = match.group(1)
          text = match.group(2)
          text = text.strip()

          component = components.get(keyword, [])
          component.append('- `{}`: {}'.format(param, text))
          components[keyword] = component
          continue

        match = re.match(r':(?:return|returns)\s*:(.*)?$', line)
        if match:
          keyword = 'Returns'
          text = match.group(1)
          text = text.strip()

          component = components.get(keyword, [])
          component.append(text)
          components[keyword] = component
          continue

        match = re.match(':(?:raises|raise)\s+(\w+)\s*:(.*)?$', line)
        if match:
          keyword = 'Raises'
          exception = match.group(1)
          text = match.group(2)
          text = text.strip()

          component = components.get(keyword, [])
          component.append('- `{}`: {}'.format(exception, text))
          components[keyword] = component
          continue

      if keyword is not None:
        components[keyword].append(line)
      else:
        nodes.append(Text(line + '\n'))

    for key, items in components.items():
      if not items: continue
      nodes.append(Text('\n\n'))
      nodes.append(Text('**{}**:\n'.format(key)))
      nodes.extend(Text(x + '\n') for x in items)

    node.substitute(nodes)


class Renderer(nr.interface.Implementation):
  """
  This is the default renderer implementation that produces hybrid
  Markdown/HTML files.

  # Options

  render_toc (bool):
    Render a table of contents in every document (#Trueby default).
  render_toc_depth (int):
    The maximum depth of the table of contents. (2 by default).
  render_section_kind (bool):
    Render the section kind into every header. (#True by default).
  render_signature_block (bool):
    Render a function signature in a code block. If disabled, the
    signature will instead be rendered in a blockquote. (#False by default)
  """

  nr.interface.implements(IRenderer)

  @nr.interface.override
  def render(self, directory, root):
    for document in root.documents:
      with open(os.path.join(directory, doc.path + '.md'), 'w') as fp:
        self.render_document(fp, document)

  @nr.interface.override
  def render_document(self, fp, doc):
    render_toc = getattr(self.config, 'render_toc', True)
    toc_depth = getattr(self.config, 'render_toc_depth', 2)
    if render_toc:
      fp.write('__Table of Contents__\n\n')
      for section in doc.hierarchy(filter=lambda x: isinstance(x, Section)):
        if section.depth > toc_depth: continue
        fp.write('    ' * (section.depth - 1))
        fp.write('* [{}](#py-{})'.format(section.label, section.id))
        fp.write('\n')
      fp.write('\n')

    self.render_node(fp, doc)

  def render_node(self, fp, node):
    if isinstance(node, Document):
      for child in node.children:
        self.render_node(fp, child)
    elif isinstance(node, Section):
      prefix = ''
      if getattr(self.config, 'render_section_kind', True) and node.kind:
        prefix = '<small>{}</small> '.format(node.kind)
      print(
        '<h{depth} id="py-{id}">{prefix}{title}</h{depth}>\n'.format(
          prefix=prefix,
          depth=node.depth,
          id=node.id,
          title=node.label
        ),
        file=fp
      )
      if node.signature:
        if getattr(self.config, 'render_signature_block', True):
          fp.write('```python\n{}\n```\n'.format(node.signature))
        else:
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
