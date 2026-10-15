from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.database import SessionLocal
from app.services.rag_service import RAGDocumentInput, RAGService


def _parse_date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _load_manifest(path: Path) -> list[dict]:
    records = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Manifest line {line_number} is not valid JSON.") from exc
    if not records:
        raise ValueError("Manifest contains no document records.")
    return records


def _ingest_manifest(path: Path) -> int:
    records = _load_manifest(path)
    service = RAGService()
    with SessionLocal() as db:
        try:
            for record in records:
                if not isinstance(record, dict):
                    raise ValueError("Each manifest row must be a JSON object.")
                content_path = (path.parent / record.pop("content_file")).resolve()
                if not content_path.is_relative_to(path.parent.resolve()):
                    raise ValueError("A document content_file must resolve beneath the manifest directory.")
                content = content_path.read_text(encoding="utf-8")
                service.ingest_document(
                    db,
                    RAGDocumentInput(
                        title=record["title"],
                        source_url=record["source_url"],
                        content=content,
                        publication_date=_parse_date(record.get("publication_date")),
                        updated_at=_parse_date(record.get("updated_at")),
                        version=record["version"],
                        licence=record["licence"],
                        allowed_use=record["allowed_use"],
                        provenance=record["provenance"],
                        category="public_health",
                        language=record.get("language", "en"),
                        summary=record.get("summary"),
                        metadata=record.get("metadata"),
                    ),
                )
            db.commit()
        except Exception:
            db.rollback()
            raise
    return len(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Idempotently ingest locally reviewed public-health documents; this tool does not download source content."
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--manifest", type=Path, help="JSONL manifest with content_file paths and source/licence metadata.")
    action.add_argument("--list-stale", action="store_true", help="List active documents older than the age threshold.")
    parser.add_argument("--max-age-days", type=int, default=180)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    service = RAGService()
    if args.list_stale:
        with SessionLocal() as db:
            stale = service.refresh_outdated_documents(db, max_age_days=args.max_age_days)
            print(json.dumps([
                {
                    "title": item.title,
                    "source_url": item.source_url,
                    "version": item.version,
                    "last_updated_or_retrieved": (item.updated_at or item.retrieval_date).isoformat(),
                }
                for item in stale
            ], indent=2))
        return 0

    path = args.manifest.resolve()
    count = _ingest_manifest(path)
    print(json.dumps({"documents_ingested_or_refreshed": count, "manifest": str(path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
