"""
Script de seed da Knowledge Base com post-mortems reais.
Uso: python -m app.scripts.seed_kb [--docs-path /path/to/post-mortems]

Cada post-mortem é dividido em chunks de ~500 chars com overlap de 50 chars
para preservar contexto nos resultados de busca semântica.
"""

import asyncio
import argparse
import re
import sys
from pathlib import Path


CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def _split_into_chunks(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Divide texto em chunks com overlap para preservar contexto."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # Overlap: mantém final do chunk anterior
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = f"{overlap_text}\n\n{para}".strip() if overlap_text else para

    if current:
        chunks.append(current)

    return chunks


def _extract_incident_id(filename: str) -> str:
    match = re.match(r"(INC-\d+)", filename)
    return match.group(1) if match else filename.replace(".md", "")


async def seed(docs_path: Path) -> None:
    # Import aqui para não exigir Qdrant em testes unitários do script
    from app.services import embedding_service, qdrant_service

    await qdrant_service.ensure_collection()

    md_files = sorted(docs_path.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {docs_path}")
        return

    total_chunks = 0
    for md_file in md_files:
        incident_id = _extract_incident_id(md_file.name)
        content = md_file.read_text(encoding="utf-8")
        chunks = _split_into_chunks(content)

        print(f"  {md_file.name} → {len(chunks)} chunks (incident_id={incident_id})")

        for i, chunk in enumerate(chunks):
            import uuid
            chunk_id = str(uuid.uuid4())
            vector = embedding_service.encode(chunk)
            await qdrant_service.upsert(
                chunk_id=chunk_id,
                vector=vector,
                payload={
                    "content": chunk,
                    "incident_id": incident_id,
                    "source_file": md_file.name,
                    "chunk_index": i,
                },
            )
            total_chunks += 1

    print(f"\nSeed complete: {len(md_files)} files, {total_chunks} chunks ingested.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Knowledge Base with post-mortems")
    parser.add_argument(
        "--docs-path",
        type=Path,
        default=Path(__file__).parent.parent.parent.parent / "docs" / "post-mortems",
        help="Path to post-mortems directory",
    )
    args = parser.parse_args()

    if not args.docs_path.exists():
        print(f"Error: {args.docs_path} does not exist")
        sys.exit(1)

    print(f"Seeding KB from: {args.docs_path}")
    asyncio.run(seed(args.docs_path))


if __name__ == "__main__":
    main()
