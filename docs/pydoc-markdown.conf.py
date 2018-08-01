
docprefix = 'content/api'

modules = [
  ('$$index', 'content/_private/api.md'),
  'pydoc_markdown.core++',
  'pydoc_markdown.core.interface++',
  'pydoc_markdown.core.document++',
  'pydoc_markdown.utils.decorators++',
  'pydoc_markdown.utils.imputils++',
  'pydoc_markdown.utils.pydoc++',
]

copy_files = [
  ('index.md', 'content/index.md'),
  ('api.md', 'content/api.md'),
  ('../README.md', 'content/_private/README.md'),
  '.statigen.toml'
]


def on_complete():
  call(['statigen'], cwd=builddir)
