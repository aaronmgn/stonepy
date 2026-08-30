"""Generate one API reference page per ``stonepy.models`` DTO and enum.

Run automatically by the ``mkdocs-gen-files`` plugin at build time. The pages are
materialised in-memory (nothing is written to the repository) and grouped into a
navigable tree by ``mkdocs-literate-nav`` via the generated ``SUMMARY.md``.
"""

from __future__ import annotations

import enum

import mkdocs_gen_files

import stonepy.models as models

nav = mkdocs_gen_files.Nav()


def _category(name: str, obj: object) -> str:
    if isinstance(obj, type) and issubclass(obj, enum.Enum):
        return "Enums"
    if name.endswith("RequestDTO"):
        return "Request models"
    if name.endswith("ResponseDTO"):
        return "Response models"
    return "Other models"


for name in sorted(models.__all__):
    obj = getattr(models, name)
    category = _category(name, obj)
    doc_path = f"reference/models/{name}.md"
    # Models live in a module named after their single class, so the bare ``stonepy.models.<name>``
    # path is ambiguous (module vs re-exported class) and renders the class wrapped in a module
    # heading. Target the class by its canonical ``module.Class`` path so the page renders the
    # class directly. Enums share one ``enums`` module, so the bare path already names the class.
    is_enum = isinstance(obj, type) and issubclass(obj, enum.Enum)
    identifier = f"stonepy.models.{name}" if is_enum else f"stonepy.models.{name}.{name}"
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"# {name}\n\n::: {identifier}\n")
    nav[(category, name)] = f"{name}.md"

with mkdocs_gen_files.open("reference/models/SUMMARY.md", "w") as fd:
    fd.writelines(nav.build_literate_nav())
