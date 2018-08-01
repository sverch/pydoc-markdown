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


import inspect
import types


def trim(docstring):
  """
  Trims whitespace from docstrings.
  """

  if not docstring:
    return ''
  lines = [x.rstrip() for x in docstring.split('\n')]
  lines[0] = lines[0].lstrip()

  indent = None
  for i, line in enumerate(lines):
    if i == 0 or not line: continue
    new_line = line.lstrip()
    delta = len(line) - len(new_line)
    if indent is None:
      indent = delta
    elif delta > indent:
      new_line = ' ' * (delta - indent) + new_line
    lines[i] = new_line

  return '\n'.join(lines)


def get_docstring(function):
  if hasattr(function, '__name__') or hasattr(function, '__doc__'):
    return function.__doc__ or ''
  else:
    return function.__call__.__doc__ or ''


def get_function_signature(function, owner_class=None, show_module=False):
  isclass = inspect.isclass(function)

  # Get base name.
  name_parts = []
  if show_module:
    name_parts.append(function.__module__)
  if owner_class:
    name_parts.append(owner_class.__name__)
  if hasattr(function, '__name__'):
    name_parts.append(function.__name__)
  else:
    name_parts.append(type(function).__name__)
    name_parts.append('__call__')
    function = function.__call__
  name = '.'.join(name_parts)

  if isclass:
    function = function.__init__
  if hasattr(inspect, 'signature'):
    sig = str(inspect.signature(function))
  else:
    argspec = inspect.getargspec(function)
    # Generate the argument list that is separated by colons.
    args = argspec.args[:]
    if argspec.defaults:
      offset = len(args) - len(argspec.defaults)
      for i, default in enumerate(argspec.defaults):
        args[i + offset] = '{}={!r}'.format(args[i + offset], argspec.defaults[i])
    if argspec.varargs:
      args.append('*' + argspec.varargs)
    if argspec.keywords:
      args.append('**' + argspec.keywords)
    sig = '(' + ', '.join(args) + ')'

  return name + sig


def dir_object(obj, sort_order='name', need_docstring=True):
  """
  Lists the members of an object suitable for documentation purposes.
  """

  assert sort_order in ('name', 'line')

  __all__ = getattr(obj, '__all__', None)

  by_name = []
  by_lineno = []


  prefix = None
  if isinstance(obj, types.ModuleType):
    prefix = obj.__name__


  for key, value in getattr(obj, '__dict__', {}).items():
    if (__all__ is None and key.startswith('_')) or \
        (__all__ is not None and key not in __all__):
      continue
    if not hasattr(value, '__doc__') or not (callable(value) or is_descriptor(value)):
      continue
    if hasattr(value, '__doc__') and need_docstring and not value.__doc__:
      continue

    # Skip imported module members.
    if isinstance(obj, types.ModuleType) and \
        getattr(value, '__module__', None) != obj.__name__:
      continue


    if sort_order == 'line':
      try:
        by_lineno.append((key, inspect.getsourcelines(value)[1]))
      except TypeError:
        # some members don't have (retrievable) line numbers (e.g., properties)
        # so fall back to sorting those first, and by name
        by_name.append(key)
    else:
      by_name.append(key)

  by_name = sorted(by_name, key=lambda s: s.lower())
  by_lineno = [key for key, lineno in sorted(by_lineno, key=lambda r: r[1])]
  return by_name + by_lineno


def is_descriptor(x):
  return hasattr(x, '__get__')
