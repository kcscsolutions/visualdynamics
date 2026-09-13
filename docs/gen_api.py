"""Write an API page per module, at build time, from the package itself.

Run by `mkdocs-gen-files` during the site build: nothing here is
committed, so the reference cannot drift from the code — it *is* the
code, read by griffe and rendered by mkdocstrings. Adding a module
documents it; adding a method documents it; changing a signature changes
the page.

What goes in it and in what order is `api_layout.py`, which is
importable on its own; this file is the part that writes, and importing
it *runs* it, which is how a gen-files script is meant to behave.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mkdocs_gen_files

# mkdocs-gen-files runs this with `runpy.run_path`, which does not put
# the script's own directory on the path — so importing the sibling that
# holds the layout has to say where it is.
sys.path.insert(0, str(Path(__file__).parent))

from api_layout import grouped, leaf_of, modules


def write_page(module: str) -> str:
    """One page of mkdocstrings directives. Returns its path."""
    path = f'api/{module}.md'
    with mkdocs_gen_files.open(path, 'w') as page:
        print(f'# `{module}`', file=page)
        print(file=page)
        print(f'::: {module}', file=page)
    return path


def main() -> None:
    for module in modules():
        write_page(module)
    groups = grouped()

    # literate-nav turns a nested list into nested navigation, and
    # Material collapses each package into a dropdown. The link text is
    # the leaf name: the full path is on the page's own heading, where
    # there is room for it.
    with mkdocs_gen_files.open('api/SUMMARY.md', 'w') as summary:
        print('* [API reference](index.md)', file=summary)
        for package, _blurb, found in groups:
            print(f'* {package}', file=summary)
            for module in found:
                print(f'    * [{leaf_of(module)}]({module}.md)', file=summary)

    with mkdocs_gen_files.open('api/index.md', 'w') as index_page:
        print('# API reference', file=index_page)
        print(file=index_page)
        print('Generated from the code on every build — every signature,',
              file=index_page)
        print('every attribute and every description here is the one the',
              file=index_page)
        print('interpreter sees. The hand-written guides, which explain',
              file=index_page)
        print('*why*, are under [Guides](../guide/README.md).',
              file=index_page)
        print(file=index_page)
        for package, blurb, found in groups:
            print(f'## `{package}`', file=index_page)
            print(file=index_page)
            if blurb:
                print(blurb, file=index_page)
                print(file=index_page)
            for module in found:
                print(f'- [`{leaf_of(module)}`]({module}.md)', file=index_page)
            print(file=index_page)


main()
