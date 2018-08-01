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
from pydoc_markdown.core import GroupPreprocessor
from pydoc_markdown.core.document import DocumentRoot, Document
from pydoc_markdown.utils.imputils import import_object
from pydoc_markdown.utils.decorators import onreturn

import argparse
import os
import shutil
import signal
import subprocess
import six
import sys
import types


PYDOC_MARKDOWN_CONFIG = 'pydoc-markdown.conf.py'


def get_argument_parser(prog):
  parser = argparse.ArgumentParser(prog=prog, description='''
    Produces Markdown files from Python modules defined in the
    pydoc-markdown.conf.py configuration file or as specified via
    the command-line.
  ''')
  parser.add_argument('modules', nargs='*', help='Specify one or more module '
    'to generate Markdown documentation files for. Appending a + to the '
    'module name will cause one additional level of objects to be taken into '
    'account. Use ++ to include class members.')
  parser.add_argument('--plain', action='store_true',
    help='Generate a single Markdown file and write it to stdout.')
  parser.add_argument('-o', '--output', type=argparse.FileType('w'), help=
    'The output file for the --plain mode.')
  parser.add_argument('--builddir', help='Override the build directory.')
  parser.add_argument('--config', help='Override the configuration filename.')
  parser.add_argument('--filter', help='Override the filter option. Must be '
    'a comma-separated list of strings. If a string starts with a - sign, it '
    'will be removed from the filter list again.')
  parser.add_argument('--sorting', help='Override the sorting option. Must '
    ' be "name" or "line".')
  return parser


def load_config(filename=None):
  """
  Loads the pydoc-markdown Python configuration file and initializes the
  default values.
  """

  if filename is None:
    required = False
    filename = PYDOC_MARKDOWN_CONFIG
  else:
    required = True

  mod = types.ModuleType('pydoc-markdown-config')
  mod.__file__ = filename
  d = vars(mod)

  try:
    with open(filename) as fp:
      six.exec_(fp.read(), d)
  except (IOError, OSError):
    if required:
      raise

  d.setdefault('modules', [])
  d.setdefault('builddir', 'build/pydoc-markdown')
  d.setdefault('loader', 'pydoc_markdown.core.PythonLoader')
  d.setdefault('preprocessor', 'pydoc_markdown.core.PydocMarkdownPreprocesor,pydoc_markdown.core.SphinxMarkdownPreprocessor')
  d.setdefault('renderer', 'pydoc_markdown.core.Renderer')
  d.setdefault('sorting', 'line')
  d.setdefault('filter', ['docstring'])

  return mod


def makedirs(path):
  """
  Create the directory *path* if it does not already exist.
  """

  if not os.path.isdir(path):
    os.makedirs(path)


@onreturn()
def main(argv=None, prog=None, onreturn=None):
  # Make sure we find local Python modules before any other.
  sys.path.append('.')
  onreturn.do(lambda: sys.path.remove('.'))

  parser = get_argument_parser(prog)
  args = parser.parse_args(argv)
  config = load_config(args.config)

  modules = args.modules or config.modules
  if not modules:
    parser.error('no modules specified')

  if args.sorting:
    if args.sorting not in ('name', 'line'):
      parser.error('invalid --sort: {!r}'.format(args.sorting))
    config.sorting = args.sorting

  if args.filter:
    for item in args.filter.split(','):
      if item.startswith('-'):
        item = item[1:]
        if item in config.filter:
          config.filter.remove(item)
      elif item not in config.filter:
        config.filter.append(item)

  if isinstance(config.loader, str):
    config.loader = import_object(config.loader)()
  if isinstance(config.preprocessor, str):
    preprocs = [x.strip() for x in config.preprocessor.split(',') if x.strip()]
    if len(preprocs) == 1:
      config.preprocessor = import_object(preprocs[0])()
    else:
      config.preprocessor = GroupPreprocessor()
      for name in preprocs:
        config.preprocessor.add(import_object(name)())
  if isinstance(config.renderer, str):
    config.renderer = import_object(config.renderer)()

  config.loader.config = config
  config.preprocessor.config = config
  config.renderer.config = config

  for i, module in enumerate(modules):
    if isinstance(module, str):
      basename = module.partition(',')[0].rstrip('+')
      modules[i] = (basename + '.md', module)

  # Loader
  root = DocumentRoot()
  for filename, module in modules:
    doc = Document(filename)  # TODO: Split extension..?
    [config.loader.load_document(modspec, doc) for modspec in module.split(',')]
    root.append(doc)

  # Preprocessor
  config.preprocessor.preprocess(root)

  if args.plain:
    document = Document('index')
    for doc in root.documents:
      for child in list(doc.children):
        document.append(child)
      doc.remove()
    root.append(document)

  if args.plain:
    config.renderer.render_document(args.output or sys.stdout, document)
  else:
    for document in root.documents:
      filename = os.path.join(config.builddir, document.path)
      makedirs(os.path.dirname(filename))
      with open(filename, 'w') as out:
        config.renderer.render_document(out, document)


if __name__ == '__main__':
  sys.exit(main())
