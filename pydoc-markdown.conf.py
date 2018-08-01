
docprefix = 'content'

modules = [
  'pydoc_markdown.core++',
  'pydoc_markdown.core.interface++',
  'pydoc_markdown.core.document++',
  'pydoc_markdown.utils.decorators++',
  'pydoc_markdown.utils.imputils++',
  'pydoc_markdown.utils.pydoc++',
]

copy_files = [
  ('README.md', 'content/index.md'),
  '.statigen.toml'
]


def on_complete():
  call(['statigen'], cwd=builddir)
