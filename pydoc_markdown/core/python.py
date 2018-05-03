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


from . import base
from .document import Document, Section
from ..utils import imputils
from ..utils.pydoc import dir_object, get_docstring, get_function_signature, trim
import inspect
import re


class PythonLoader(base.Loader):
  """
  Expects absolute identifiers to import with #import_object_with_scope().
  """

  def load_document(self, modspec):
    levels, modspec = len(modspec), modspec.rstrip('+')
    levels -= len(modspec)
    return self._build_document(Document(), modspec, levels+1)

  def _load_section(self, name, depth):
    obj, scope = imputils.import_object_with_scope(name)

    if '.' in name:
      default_title = name.rsplit('.', 1)[1]
    else:
      default_title = name

    title = getattr(obj, '__name__', default_title)
    if isinstance(obj, type):
      title += ' objects'
    else:
      title += '()'
    content = trim(get_docstring(obj))

    # Add the function signature in a code-block.
    if callable(obj):
      sig = get_function_signature(obj, scope if inspect.isclass(scope) else None)
      content = '```python\n{}\n```\n'.format(sig) + content

    section = Section(name, title, depth, content)
    section.loader_context = {'obj': obj, 'scope': scope}
    return section

  def _build_document(self, doc, name, max_depth, depth=1):
    if depth > max_depth:
      return

    try:
      sec = self._load_section(name, depth)
    except Exception:
      print('Error while loading "{}"'.format(name))
      raise
    doc.add_section(sec)

    sort_order = getattr(self.config, 'sorting', 'line')
    for sub in dir_object(sec.loader_context['obj'], sort_order):
      sub = name + '.' + sub
      self._build_document(doc, sub, max_depth, depth+1)
    return doc


class Preprocessor(base.Preprocessor):
  """
  This class implements the basic pydoc-markdown preprocessing.

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

  def process_document(self, index, document):
    pass

  def process_section(self, index, section):
    """
    Preprocess the contents of *section*.
    """

    lines = []
    codeblock_opened = False
    current_section = None
    for line in section.content.split('\n'):
      if line.startswith("```"):
        codeblock_opened = (not codeblock_opened)
      if not codeblock_opened:
        line, current_section = self._preprocess_line(line, current_section)
      lines.append(line)
    section.content = self._preprocess_refs('\n'.join(lines))

  def _preprocess_line(self, line, current_section):
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

    return line, current_section

  def _preprocess_refs(self, content):
    # TODO: Generate links to the referenced symbols.
    def handler(match):
      ref = match.group(1)
      parens = match.group(2) or ''
      has_trailing_dot = False
      if not parens and ref.endswith('.'):
        ref = ref[:-1]
        has_trailing_dot = True
      result = '`{}`'.format(ref + parens)
      if has_trailing_dot:
        result += '.'
      return result
    return re.sub('\B#([\w\d\._]+)(\(\))?', handler, content)
