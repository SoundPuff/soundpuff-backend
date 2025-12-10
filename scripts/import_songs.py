"""Utility script for importing songs from a CSV file into the database.

Example usage (after downloading the dataset with the Kaggle CLI)::

    uv run python scripts/import_songs.py \
        --dataset data/songs-.zip \
        --csv-name songs.csv

The script tries to autodetect common column names for title, artist, song
URL, and album art URL. If detection fails, you can override the column names
with the explicit flags below.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional, Tuple

from sqlalchemy import and_, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import Song

DEFAULT_TITLE_COLUMNS = (
    "title",
    "song",
    "song_name",
    "track",
    "track_name",
    "name",
)
DEFAULT_ARTIST_COLUMNS = (
    "artist",
    "artists",
    "artist_name",
    "singer",
)
DEFAULT_URL_COLUMNS = (
    "song_url",
    "url",
    "link",
    "spotify_url",
    "youtube_url",
    "preview",
    "preview_url",
)
DEFAULT_ALBUM_ART_COLUMNS = (
    "album_art",
    "album_art_url",
    "image_url",
    "img",
    "cover_url",
)


def _open_csv(dataset_path: Path, csv_name: Optional[str]) -> Tuple[Iterator[Dict[str, str]], Iterable[str]]:
    """Open a CSV file directly or from inside a ZIP archive.

    Returns an iterator of rows and the fieldnames detected by the DictReader.
    """

    if dataset_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(dataset_path) as archive:
            target_name = csv_name
            if target_name is None:
                target_name = next(
                    (name for name in archive.namelist() if name.lower().endswith(".csv")),
                    None,
                )
            if target_name is None:
                raise FileNotFoundError(
                    "No CSV file found inside the provided ZIP archive. Use --csv-name to specify it explicitly."
                )

            file_handle = archive.open(target_name)
            text_stream = io.TextIOWrapper(file_handle, encoding="utf-8")
            reader = csv.DictReader(text_stream)
            return reader, reader.fieldnames or []

    text_stream = dataset_path.open("r", encoding="utf-8", newline="")
    reader = csv.DictReader(text_stream)
    return reader, reader.fieldnames or []


def _resolve_dataset_file(dataset_path: Path, csv_name: Optional[str]) -> Tuple[Path, Optional[str]]:
    """Resolve a dataset path that could be a file or a directory.

    This makes it easier to use paths returned by KaggleHub's
    ``dataset_download`` helper, which stores the dataset in a directory.
    """

    if dataset_path.is_dir():
        if csv_name:
            candidate = dataset_path / csv_name
            if not candidate.exists():
                raise FileNotFoundError(f"CSV file not found in directory: {candidate}")
            return candidate, None

        csv_files = list(dataset_path.glob("*.csv"))
        zip_files = list(dataset_path.glob("*.zip"))

        if len(csv_files) == 1:
            return csv_files[0], None
        if len(zip_files) == 1:
            return zip_files[0], None

        raise FileNotFoundError(
            "Could not resolve dataset file inside the provided directory. "
            "Specify --csv-name or pass a direct CSV/ZIP path."
        )

    return dataset_path, csv_name


def _detect_column(fieldnames: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    lowered = {field.lower(): field for field in fieldnames}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def _resolve_columns(fieldnames: Iterable[str], args: argparse.Namespace) -> Tuple[str, str, str, Optional[str]]:
    title_column = args.title_column or _detect_column(fieldnames, DEFAULT_TITLE_COLUMNS)
    artist_column = args.artist_column or _detect_column(fieldnames, DEFAULT_ARTIST_COLUMNS)
    url_column = args.url_column or _detect_column(fieldnames, DEFAULT_URL_COLUMNS)
    album_art_column = args.album_art_column or _detect_column(fieldnames, DEFAULT_ALBUM_ART_COLUMNS)

    if not title_column:
        raise ValueError("Could not detect a title column. Use --title-column to set it explicitly.")
    if not artist_column:
        raise ValueError("Could not detect an artist column. Use --artist-column to set it explicitly.")
    if not url_column:
        raise ValueError("Could not detect a song URL column. Use --url-column to set it explicitly.")

    return title_column, artist_column, url_column, album_art_column


def _create_session() -> Session:
    engine = create_engine(settings.db_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return SessionLocal()


def import_songs(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset_path, csv_name = _resolve_dataset_file(dataset_path, args.csv_name)
    if not dataset_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    reader, fieldnames = _open_csv(dataset_path, csv_name)
    title_column, artist_column, url_column, album_art_column = _resolve_columns(fieldnames, args)

    session = _create_session()
    imported = 0
    skipped = 0

    try:
        for row in reader:
            if args.limit and imported >= args.limit:
                break

            title = (row.get(title_column) or "").strip()
            artist = (row.get(artist_column) or "").strip()
            song_url = (row.get(url_column) or "").strip()
            album_art_url = (row.get(album_art_column) or "").strip() if album_art_column else None

            if not title or not artist or not song_url:
                skipped += 1
                continue

            existing = (
                session.query(Song)
                .filter(and_(Song.title == title, Song.artist == artist))
                .first()
            )
            if existing:
                skipped += 1
                continue

            song = Song(
                title=title,
                artist=artist,
                song_url=song_url,
                album_art_url=album_art_url or None,
            )
            session.add(song)
            imported += 1

            if imported % args.batch_size == 0:
                session.commit()

        session.commit()
    finally:
        session.close()

    print(f"Imported {imported} song(s). Skipped {skipped} duplicate/invalid rows.")
    return imported


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import songs from a CSV dataset")
    parser.add_argument(
        "--dataset",
        required=True,
        help="Path to the CSV/ZIP dataset file or directory containing it",
    )
    parser.add_argument("--csv-name", help="CSV filename inside the ZIP archive, if applicable")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of rows imported")
    parser.add_argument("--batch-size", type=int, default=500, help="Rows to commit in each batch")
    parser.add_argument("--title-column", help="Override the title column name")
    parser.add_argument("--artist-column", help="Override the artist column name")
    parser.add_argument("--url-column", help="Override the song URL column name")
    parser.add_argument("--album-art-column", help="Override the album art URL column name")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    return import_songs(args)


if __name__ == "__main__":
    sys.exit(main())