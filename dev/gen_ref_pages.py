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
    with mkdocs_gen_files.open(doc_path, "w") as fd:
        fd.write(f"# {name}\n\n::: stonepy.models.{name}\n")
    nav[(category, name)] = f"{name}.md"

with mkdocs_gen_files.open("reference/models/SUMMARY.md", "w") as fd:
    fd.writelines(nav.build_literate_nav())
