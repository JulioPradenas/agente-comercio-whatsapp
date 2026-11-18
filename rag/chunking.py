"""Divide las políticas en chunks: una sección `##` = un chunk."""

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

POLICIES_DIR = Path(__file__).resolve().parent.parent / "data" / "policies"
FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


@dataclass
class Chunk:
    chunk_id: str
    source: str
    section: str
    content: str

    @property
    def content_hash(self) -> str:
        return hashlib.sha256(self.content.encode()).hexdigest()


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = FRONTMATTER.match(text)
    if not match:
        return {}, text
    metadata = dict(line.split(": ", 1) for line in match.group(1).splitlines())
    return metadata, text[match.end() :]


def chunk_policy(path: Path) -> list[Chunk]:
    metadata, body = parse_frontmatter(path.read_text())
    source = metadata.get("source", path.stem)
    # La política se corta en cada "## ". Lo que va antes (el título "# ...") se descarta.
    sections = re.split(r"^## ", body, flags=re.MULTILINE)[1:]

    chunks = []
    for section in sections:
        title, _, section_body = section.partition("\n")
        chunks.append(
            Chunk(
                chunk_id=f"{path.stem}#{slugify(title)}",
                source=source,
                section=title.strip(),
                # El encabezado da contexto al embedding: "Plazo" solo es ambiguo;
                # "Política de despacho > Plazo de entrega" no lo es.
                content=f"{source} > {title.strip()}\n\n{section_body.strip()}",
            )
        )
    return chunks


def load_policy_chunks(policies_dir: Path = POLICIES_DIR) -> list[Chunk]:
    return [chunk for path in sorted(policies_dir.glob("*.md")) for chunk in chunk_policy(path)]


if __name__ == "__main__":
    chunks = load_policy_chunks()
    print(f"{len(chunks)} chunks\n")
    for chunk in chunks[:2]:
        print(f"[{chunk.chunk_id}]\n{chunk.content}\n")
