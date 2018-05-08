
### 3.0.0 (develop) from v2.0.3

- Restructure project, rename Python module from `pydocmd` to `pydoc_markdown`
- No longer supports MkDocs natively, MkDocs needs to be invoked separately
- CLI overhaul
- Configuration is now a Python script `pydoc-markdown.conf.py`
- Add `--sorting` and `--filter` (#43) options

### v2.0.4 (master)

- Add `-c key=value` argument for `generate` and `simple` command
- Add `filter=["docstring"]` option (#43)

### v2.0.3

- Fix #41, #36, #31
- Merged #39

### v2.0.2 

- Fix #25 -- Text is incorrectly rendered as code
- Fix #26 -- Broken links for URLs with fragment identifiers
- No longer transforms titles in a docstring that are indented (eg. to
  avoid an indented code block with a `#` comment to be corrupted)

### v2.0.1

- Support `additional_search_path` key in configuration
- Render headers as HTML `<hX>` tags rather than Markdown tags, so we
  assign a proper ID to them
- Fix #21 -- AttributeError: 'module' object has no attribute 'signature'
- Now requires the `six` module
- FIx #22 -- No blank space after header does not render codeblocks

### v2.0.0

- Complete overhaul of **pydoc-markdown** employing MkDocs and the Markdown module.
