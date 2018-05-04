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

import argparse
import os
import shutil
import signal
import subprocess
import six
import sys
import types

from .core.document import DocumentIndex, Document
from .utils.imputils import import_object
from .utils.decorators import onreturn


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
  parser.add_argument('--builddir', help='Override the build directory.')
  parser.add_argument('--indexer', help='Override the indexer class.')
  parser.add_argument('--config', help='Override the configuration filename.')
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
  d.setdefault('preprocessor', 'pydoc_markdown.core.Preprocessor')
  d.setdefault('indexer', 'pydoc_markdown.core.base.VoidIndexer')
  d.setdefault('renderer', 'pydoc_markdown.core.base.Renderer')

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

  if isinstance(config.loader, str):
    config.loader = import_object(config.loader)()
  if isinstance(config.preprocessor, str):
    config.preprocessor = import_object(config.preprocessor)()
  if isinstance(config.indexer, str):
    config.indexer = import_object(config.indexer)()
  if isinstance(config.renderer, str):
    config.renderer = import_object(config.renderer)()

  config.loader.config = config
  config.preprocessor.config = config
  config.indexer.config = config
  config.renderer.config = config

  for i, module in enumerate(modules):
    if isinstance(module, str):
      basename = module.partition(',')[0].rstrip('+')
      modules[i] = (basename + '.md', module)

  # Loader
  index = DocumentIndex()
  for filename, module in modules:
    document = Document.join(config.loader.load_document(modspec) for
      modspec in module.split(','))
    document.filename = filename
    index.add_document(document)

  # Preprocessor
  for document in index.iter_documents():
    config.preprocessor.process_document(index, document)
    for section in document.iter_sections():
      config.preprocessor.process_section(index, section)

  if args.plain:
    document = Document.join(index.iter_documents())
    document.filename = 'index.md'
    index = DocumentIndex()
    index.add_document(document)

  # Indexer
  config.indexer.process_index(index)
  for document in index.iter_documents():
    config.indexer.process_document(index, document)

  if args.plain:
    config.renderer.render_document(sys.stdout, document)
  else:
    for filename, document in index.documents.items():
      filename = os.path.join(config.builddir, filename)
      makedirs(os.path.dirname(filename))
      with open(filename, 'w') as out:
        config.renderer.render_document(out, document)
    config.indexer.write_additional_files(index)


if __name__ == '__main__':
  sys.exit(main())
