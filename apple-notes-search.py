#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "fastembed>=0.7,<0.9",
#   "numpy>=1.26,<3",
# ]
# ///
"""Index and semantically search Apple Notes without sending note data to a cloud service.

The first sync downloads a local embedding model. Later indexing and searches run locally.

Examples:
  ./apple-notes-search.py sync
  ./apple-notes-search.py search "ideas for improving sleep"
  ./apple-notes-search.py search --limit 5 "books about decision making"
  ./apple-notes-search.py status
  ./apple-notes-search.py rebuild
"""

import argparse
import contextlib
import dataclasses
import datetime as dt
import fcntl
import hashlib
import importlib.metadata
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

APP_NAME = "apple-notes-search"
DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
SCHEMA_VERSION = 1
EXTRACTOR_VERSION = 1
CHUNKER_VERSION = "char-v1:max400:overlap60"
MAX_CHUNK_CHARS = 400
CHUNK_OVERLAP_CHARS = 60
VECTOR_DTYPE = "float32-le"

DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
DEFAULT_DB_PATH = DEFAULT_DATA_DIR / "index.sqlite3"
DEFAULT_CACHE_DIR = Path.home() / "Library" / "Caches" / APP_NAME / "models"


JXA_EXTRACT_NOTES = r"""
function errorText(error) {
    try { return String(error.message || error); } catch (_) { return "Unknown JXA error"; }
}

function safeString(getter, fallback) {
    try {
        var value = getter();
        return value === null || value === undefined ? fallback : String(value);
    } catch (_) {
        return fallback;
    }
}

function safeBoolean(getter, fallback) {
    try { return Boolean(getter()); } catch (_) { return fallback; }
}

function safeDate(getter) {
    try {
        var value = getter();
        return value ? new Date(value).toISOString() : null;
    } catch (_) {
        return null;
    }
}

function run(argv) {
    var Notes = Application("Notes");
    var includeLocked = argv.length > 0 && argv[0] === "true";
    var envelope = {
        extractor_version: 1,
        complete: true,
        accounts: [],
        notes: [],
        errors: []
    };
    var accounts;

    try {
        accounts = Notes.accounts();
    } catch (error) {
        throw new Error("Could not enumerate Notes accounts: " + errorText(error));
    }

    for (var accountIndex = 0; accountIndex < accounts.length; accountIndex++) {
        var account = accounts[accountIndex];
        var accountId;
        try {
            accountId = String(account.id());
        } catch (error) {
            envelope.complete = false;
            envelope.errors.push({scope: "account", error: errorText(error)});
            continue;
        }

        var accountName = safeString(function () { return account.name(); }, "Unknown account");
        var folderPaths = {};
        var visitedFolders = {};

        function visitFolder(folder, parentPath) {
            var folderId;
            try {
                folderId = String(folder.id());
            } catch (error) {
                envelope.errors.push({scope: "folder", account_id: accountId, error: errorText(error)});
                return;
            }
            var folderKey = "$" + folderId;
            if (visitedFolders[folderKey]) return;
            visitedFolders[folderKey] = true;

            var folderName = safeString(function () { return folder.name(); }, "Unknown folder");
            var path = parentPath ? parentPath + "/" + folderName : folderName;
            folderPaths[folderKey] = path;

            try {
                var children = folder.folders();
                for (var childIndex = 0; childIndex < children.length; childIndex++) {
                    visitFolder(children[childIndex], path);
                }
            } catch (error) {
                envelope.errors.push({scope: "folder-children", folder_id: folderId, error: errorText(error)});
            }
        }

        try {
            var folders = account.folders();
            for (var folderIndex = 0; folderIndex < folders.length; folderIndex++) {
                visitFolder(folders[folderIndex], "");
            }
        } catch (error) {
            envelope.errors.push({scope: "folders", account_id: accountId, error: errorText(error)});
        }

        var accountRecord = {id: accountId, name: accountName, complete: true};
        envelope.accounts.push(accountRecord);
        var notes;
        try {
            notes = account.notes();
        } catch (error) {
            accountRecord.complete = false;
            envelope.complete = false;
            envelope.errors.push({scope: "notes", account_id: accountId, error: errorText(error)});
            continue;
        }

        var seenNoteIds = {};
        for (var noteIndex = 0; noteIndex < notes.length; noteIndex++) {
            var note = notes[noteIndex];
            var noteId;
            try {
                noteId = String(note.id());
            } catch (error) {
                accountRecord.complete = false;
                envelope.complete = false;
                envelope.errors.push({scope: "note-id", account_id: accountId, error: errorText(error)});
                continue;
            }

            var noteKey = "$" + noteId;
            if (seenNoteIds[noteKey]) {
                accountRecord.complete = false;
                envelope.complete = false;
                envelope.errors.push({scope: "duplicate-note", account_id: accountId, note_id: noteId});
                continue;
            }
            seenNoteIds[noteKey] = true;

            var folderId = null;
            var folderPath = "";
            try {
                var container = note.container();
                folderId = String(container.id());
                folderPath = folderPaths["$" + folderId] || safeString(function () { return container.name(); }, "");
            } catch (error) {
                envelope.errors.push({scope: "note-folder", account_id: accountId, note_id: noteId,
                                      error: errorText(error)});
            }

            var text = null;
            var contentError = null;
            var contentState = "available";
            var passwordProtected = true;
            try {
                passwordProtected = Boolean(note.passwordProtected());
            } catch (error) {
                contentState = "locked_excluded";
                contentError = "Could not determine whether the note is password-protected: " + errorText(error);
            }

            if (contentState === "available" && passwordProtected && !includeLocked) {
                contentState = "locked_excluded";
                contentError = "Password-protected note excluded";
            } else if (contentState === "available") {
                try {
                    text = String(note.plaintext());
                } catch (error) {
                    contentState = "unavailable";
                    contentError = errorText(error);
                    envelope.errors.push({scope: "note-content", account_id: accountId, note_id: noteId,
                                          error: contentError});
                }
            }

            envelope.notes.push({
                account_id: accountId,
                account_name: accountName,
                note_id: noteId,
                title: safeString(function () { return note.name(); }, "Untitled note"),
                folder_id: folderId,
                folder_path: folderPath,
                created_at: safeDate(function () { return note.creationDate(); }),
                modified_at: safeDate(function () { return note.modificationDate(); }),
                password_protected: passwordProtected,
                shared: safeBoolean(function () { return note.shared(); }, false),
                text: text,
                content_state: contentState,
                content_error: contentError
            });
        }
    }

    return JSON.stringify(envelope);
}
"""


JXA_OPEN_NOTE = r"""
function run(argv) {
    var targetAccountId = argv[0];
    var targetNoteId = argv[1];
    var Notes = Application("Notes");
    var accounts = Notes.accounts();
    for (var accountIndex = 0; accountIndex < accounts.length; accountIndex++) {
        var account = accounts[accountIndex];
        if (String(account.id()) !== targetAccountId) continue;
        var notes = account.notes();
        for (var noteIndex = 0; noteIndex < notes.length; noteIndex++) {
            var note = notes[noteIndex];
            if (String(note.id()) === targetNoteId) {
                Notes.show(note);
                Notes.activate();
                return JSON.stringify({ok: true});
            }
        }
    }
    return JSON.stringify({ok: false, error: "Note not found in Apple Notes"});
}
"""


@dataclasses.dataclass(frozen=True)
class Note:
    account_id: str
    account_name: str
    note_id: str
    title: str
    folder_id: str | None
    folder_path: str
    created_at: str | None
    modified_at: str | None
    password_protected: bool
    shared: bool
    text: str | None
    content_state: str
    content_error: str | None


@dataclasses.dataclass(frozen=True)
class ExtractedNotes:
    notes: list[Note]
    complete: bool
    errors: list[dict[str, Any]]
    account_count: int


class UserError(RuntimeError):
    """An actionable command-line error."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def fastembed_version() -> str:
    try:
        return importlib.metadata.version("fastembed")
    except importlib.metadata.PackageNotFoundError:
        return "not-installed"


def index_signature(model_name: str) -> str:
    return json.dumps(
        {
            "chunker": CHUNKER_VERSION,
            "embedding_modes": ["passage", "query"],
            "fastembed": fastembed_version(),
            "model": model_name,
            "vector_dtype": VECTOR_DTYPE,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def normalize_text(title: str, text: str) -> str:
    title = title.replace("\x00", " ").strip()
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    if not text:
        return title
    if title and not text.casefold().startswith(title.casefold()):
        return f"{title}\n\n{text}"
    return text


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(
    text: str,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap_chars: int = CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """Split text on nearby boundaries with a conservative embedding-model limit."""
    if max_chars < 1 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size")
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    boundaries = ("\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ")
    while start < len(text):
        hard_end = min(start + max_chars, len(text))
        end = hard_end
        if hard_end < len(text):
            minimum_end = start + max_chars // 2
            candidates = [text.rfind(boundary, minimum_end, hard_end) for boundary in boundaries]
            boundary = max(candidates)
            if boundary >= minimum_end:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap_chars)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start
    return chunks


def parse_extracted_notes(payload: str) -> ExtractedNotes:
    try:
        envelope = json.loads(payload)
    except json.JSONDecodeError as error:
        raise UserError(f"Apple Notes returned malformed data: {error}") from error

    if not isinstance(envelope, dict) or envelope.get("extractor_version") != EXTRACTOR_VERSION:
        raise UserError("Apple Notes returned an unsupported extraction format")
    if not isinstance(envelope.get("complete"), bool):
        raise UserError("Apple Notes extraction did not report whether its ID inventory was complete")
    if not isinstance(envelope.get("notes"), list) or not isinstance(envelope.get("accounts"), list):
        raise UserError("Apple Notes extraction omitted accounts or notes")

    notes: list[Note] = []
    identities: set[tuple[str, str]] = set()
    for item in envelope["notes"]:
        if not isinstance(item, dict):
            raise UserError("Apple Notes returned an invalid note record")
        account_id = item.get("account_id")
        note_id = item.get("note_id")
        if not isinstance(account_id, str) or not account_id or not isinstance(note_id, str) or not note_id:
            raise UserError("Apple Notes returned a note without a stable account/note ID")
        identity = (account_id, note_id)
        if identity in identities:
            raise UserError(f"Apple Notes returned duplicate note ID {note_id!r}")
        identities.add(identity)

        text = item.get("text")
        notes.append(
            Note(
                account_id=account_id,
                account_name=str(item.get("account_name") or "Unknown account"),
                note_id=note_id,
                title=str(item.get("title") or "Untitled note"),
                folder_id=str(item["folder_id"]) if item.get("folder_id") is not None else None,
                folder_path=str(item.get("folder_path") or ""),
                created_at=str(item["created_at"]) if item.get("created_at") is not None else None,
                modified_at=str(item["modified_at"]) if item.get("modified_at") is not None else None,
                password_protected=bool(item.get("password_protected")),
                shared=bool(item.get("shared")),
                text=str(text) if text is not None else None,
                content_state=str(item.get("content_state") or ("available" if text is not None else "unavailable")),
                content_error=str(item["content_error"]) if item.get("content_error") is not None else None,
            )
        )

    errors = envelope.get("errors", [])
    if not isinstance(errors, list):
        raise UserError("Apple Notes extraction returned an invalid error list")
    return ExtractedNotes(notes, envelope["complete"], errors, len(envelope["accounts"]))


def extract_notes(include_locked: bool = False) -> ExtractedNotes:
    try:
        completed = subprocess.run(
            [
                "/usr/bin/osascript",
                "-l",
                "JavaScript",
                "-e",
                JXA_EXTRACT_NOTES,
                str(include_locked).lower(),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        detail = (error.stderr or error.stdout or "Unknown osascript error").strip()
        if "not authorized" in detail.lower() or "-1743" in detail:
            detail += " (allow your terminal under System Settings > Privacy & Security > Automation)"
        raise UserError(f"Could not read Apple Notes: {detail}") from error
    return parse_extracted_notes(completed.stdout.strip())


def connect_database(path: Path, create: bool = True) -> sqlite3.Connection:
    if not create and not path.exists():
        raise UserError(f"Index not found at {path}. Run `sync` first.")
    if create:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.parent == DEFAULT_DATA_DIR:
            path.parent.chmod(0o700)
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(descriptor)
        path.chmod(0o600)
    try:
        connection = sqlite3.connect(path, timeout=30)
    except sqlite3.Error as error:
        raise UserError(f"Could not open index {path}: {error}") from error
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensure_schema(connection: sqlite3.Connection) -> None:
    current_version = connection.execute("PRAGMA user_version").fetchone()[0]
    if current_version not in (0, SCHEMA_VERSION):
        raise UserError(
            f"Index schema {current_version} is unsupported (expected {SCHEMA_VERSION}). "
            "Move the database aside and run `sync`."
        )
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notes (
            account_id TEXT NOT NULL,
            note_id TEXT NOT NULL,
            account_name TEXT NOT NULL,
            folder_id TEXT,
            folder_path TEXT NOT NULL,
            title TEXT NOT NULL,
            text TEXT,
            created_at TEXT,
            modified_at TEXT,
            password_protected INTEGER NOT NULL DEFAULT 0,
            shared INTEGER NOT NULL DEFAULT 0,
            content_error TEXT,
            content_hash TEXT,
            last_seen_generation TEXT NOT NULL,
            PRIMARY KEY (account_id, note_id)
        );
        CREATE TABLE IF NOT EXISTS chunks (
            account_id TEXT NOT NULL,
            note_id TEXT NOT NULL,
            ordinal INTEGER NOT NULL,
            text TEXT NOT NULL,
            vector BLOB NOT NULL,
            PRIMARY KEY (account_id, note_id, ordinal),
            FOREIGN KEY (account_id, note_id) REFERENCES notes(account_id, note_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS chunks_note_idx ON chunks(account_id, note_id);
        """)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    connection.commit()


def read_meta(connection: sqlite3.Connection) -> dict[str, str]:
    return {row["key"]: row["value"] for row in connection.execute("SELECT key, value FROM meta")}


def load_embedding_model(model_name: str, cache_dir: Path, offline: bool):
    try:
        from fastembed import TextEmbedding
    except ImportError as error:
        raise UserError(
            "fastembed is unavailable; run this script with uv or install its inline dependencies"
        ) from error

    cache_dir.mkdir(parents=True, exist_ok=True)
    kwargs: dict[str, Any] = {"model_name": model_name, "cache_dir": str(cache_dir)}
    if offline:
        kwargs["local_files_only"] = True
    try:
        with contextlib.redirect_stdout(sys.stderr):
            return TextEmbedding(**kwargs)
    except Exception as error:
        hint = " The model must already exist in the cache when --offline is used." if offline else ""
        raise UserError(f"Could not load local embedding model {model_name!r}: {error}.{hint}") from error


def call_embed(model: Any, method_name: str, texts: Sequence[str]) -> list[Any]:
    method = getattr(model, method_name, None) or getattr(model, "embed", None)
    if method is None:
        raise UserError(f"The installed fastembed version does not support {method_name}")
    try:
        with contextlib.redirect_stdout(sys.stderr):
            return list(method(texts, batch_size=64, show_progress_bar=False))
    except TypeError:
        with contextlib.redirect_stdout(sys.stderr):
            return list(method(texts, batch_size=64))
    except Exception as error:
        raise UserError(f"Local embedding failed: {error}") from error


def normalize_vectors(vectors: Iterable[Any]) -> tuple[list[bytes], int]:
    try:
        import numpy as np
    except ImportError as error:
        raise UserError("numpy is unavailable; run this script with uv or install its inline dependencies") from error

    encoded: list[bytes] = []
    dimension: int | None = None
    for vector in vectors:
        array = np.asarray(vector, dtype="<f4").reshape(-1)
        if not array.size or not np.all(np.isfinite(array)):
            raise UserError("The embedding model returned an empty or non-finite vector")
        norm = float(np.linalg.norm(array))
        if not math.isfinite(norm) or norm <= 0:
            raise UserError("The embedding model returned a zero-length vector")
        array = np.asarray(array / norm, dtype="<f4")
        if dimension is None:
            dimension = int(array.size)
        elif array.size != dimension:
            raise UserError("The embedding model returned inconsistent vector dimensions")
        encoded.append(array.tobytes(order="C"))
    return encoded, dimension or 0


@contextlib.contextmanager
def exclusive_index_lock(db_path: Path) -> Iterator[None]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = db_path.with_suffix(db_path.suffix + ".lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    os.chmod(lock_path, 0o600)
    with os.fdopen(descriptor, "a+") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise UserError(f"Another indexing process is already using {db_path}") from error
        yield


def sync_index(args: argparse.Namespace, force: bool = False) -> dict[str, Any]:
    db_path = Path(args.db).expanduser()
    cache_dir = Path(args.cache_dir).expanduser()
    with exclusive_index_lock(db_path):
        extraction = extract_notes(args.include_locked)
        connection = connect_database(db_path)
        try:
            ensure_schema(connection)
            meta = read_meta(connection)
            signature = index_signature(args.model)
            compatibility_changed = meta.get("index_signature") not in (None, signature)
            rebuild_all = force or compatibility_changed
            if rebuild_all and not extraction.complete:
                raise UserError(
                    "Apple Notes returned an incomplete ID inventory; refusing to rebuild so the existing index "
                    "remains intact. Resolve the reported Notes errors and try again."
                )
            generation = str(uuid.uuid4())

            existing = {
                (row["account_id"], row["note_id"]): row
                for row in connection.execute("SELECT account_id, note_id, text, content_hash FROM notes")
            }
            prepared: list[tuple[Note, str | None, list[str], bool]] = []
            all_chunks: list[str] = []
            excluded_count = 0

            for note in extraction.notes:
                indexed_text: str | None
                old = existing.get((note.account_id, note.note_id))
                if note.content_state == "locked_excluded":
                    indexed_text = None
                    excluded_count += 1
                elif note.content_state == "unavailable":
                    indexed_text = old["text"] if old is not None else None
                    excluded_count += 1
                elif note.text is None:
                    indexed_text = None
                    excluded_count += 1
                else:
                    indexed_text = normalize_text(note.title, note.text)

                digest = content_hash(indexed_text) if indexed_text is not None else None
                changed = rebuild_all or old is None or old["content_hash"] != digest
                chunks = chunk_text(indexed_text) if changed and indexed_text else []
                prepared.append((note, indexed_text, chunks, changed))
                all_chunks.extend(chunks)

            vector_blobs: list[bytes] = []
            dimension = int(meta.get("vector_dimension", "0"))
            if all_chunks:
                model = load_embedding_model(args.model, cache_dir, args.offline)
                raw_vectors = call_embed(model, "passage_embed", all_chunks)
                vector_blobs, dimension = normalize_vectors(raw_vectors)
                if len(vector_blobs) != len(all_chunks):
                    raise UserError("The embedding model returned fewer vectors than input chunks")
            elif rebuild_all:
                dimension = 0

            vector_offset = 0
            changed_count = 0
            connection.execute("BEGIN IMMEDIATE")
            try:
                if rebuild_all:
                    connection.execute("DELETE FROM chunks")
                for note, indexed_text, chunks, changed in prepared:
                    digest = content_hash(indexed_text) if indexed_text is not None else None
                    connection.execute(
                        """
                        INSERT INTO notes (
                            account_id, note_id, account_name, folder_id, folder_path, title, text,
                            created_at, modified_at, password_protected, shared, content_error,
                            content_hash, last_seen_generation
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(account_id, note_id) DO UPDATE SET
                            account_name = excluded.account_name,
                            folder_id = excluded.folder_id,
                            folder_path = excluded.folder_path,
                            title = excluded.title,
                            text = excluded.text,
                            created_at = excluded.created_at,
                            modified_at = excluded.modified_at,
                            password_protected = excluded.password_protected,
                            shared = excluded.shared,
                            content_error = excluded.content_error,
                            content_hash = excluded.content_hash,
                            last_seen_generation = excluded.last_seen_generation
                        """,
                        (
                            note.account_id,
                            note.note_id,
                            note.account_name,
                            note.folder_id,
                            note.folder_path,
                            note.title,
                            indexed_text,
                            note.created_at,
                            note.modified_at,
                            int(note.password_protected),
                            int(note.shared),
                            note.content_error,
                            digest,
                            generation,
                        ),
                    )
                    if changed:
                        changed_count += 1
                        connection.execute(
                            "DELETE FROM chunks WHERE account_id = ? AND note_id = ?",
                            (note.account_id, note.note_id),
                        )
                        for ordinal, chunk in enumerate(chunks):
                            connection.execute(
                                "INSERT INTO chunks (account_id, note_id, ordinal, text, vector) VALUES (?, ?, ?, ?, ?)",
                                (note.account_id, note.note_id, ordinal, chunk, vector_blobs[vector_offset]),
                            )
                            vector_offset += 1

                deleted_count = 0
                if extraction.complete:
                    deleted_count = connection.execute(
                        "SELECT COUNT(*) FROM notes WHERE last_seen_generation != ?", (generation,)
                    ).fetchone()[0]
                    connection.execute("DELETE FROM notes WHERE last_seen_generation != ?", (generation,))

                metadata = {
                    "index_signature": signature,
                    "model": args.model,
                    "vector_dimension": str(dimension),
                    "vector_dtype": VECTOR_DTYPE,
                    "last_sync_at": utc_now(),
                    "last_scan_complete": json.dumps(extraction.complete),
                }
                connection.executemany(
                    "INSERT INTO meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    metadata.items(),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        finally:
            connection.close()

    return {
        "ok": True,
        "command": "rebuild" if force else "sync",
        "database": str(db_path),
        "accounts_scanned": extraction.account_count,
        "notes_seen": len(extraction.notes),
        "notes_reindexed": changed_count,
        "notes_deleted": deleted_count,
        "notes_excluded": excluded_count,
        "chunks_embedded": len(all_chunks),
        "scan_complete": extraction.complete,
        "scan_errors": extraction.errors,
    }


def status_index(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db).expanduser()
    connection = connect_database(db_path, create=False)
    try:
        ensure_schema(connection)
        meta = read_meta(connection)
        note_count = connection.execute("SELECT COUNT(*) FROM notes").fetchone()[0]
        searchable_count = connection.execute("SELECT COUNT(*) FROM notes WHERE content_hash IS NOT NULL").fetchone()[0]
        chunk_count = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        locked_count = connection.execute("SELECT COUNT(*) FROM notes WHERE password_protected = 1").fetchone()[0]
    finally:
        connection.close()
    expected_signature = index_signature(args.model)
    return {
        "ok": True,
        "command": "status",
        "database": str(db_path),
        "model": meta.get("model"),
        "vector_dimension": int(meta.get("vector_dimension", "0")),
        "notes": note_count,
        "searchable_notes": searchable_count,
        "locked_notes": locked_count,
        "chunks": chunk_count,
        "last_sync_at": meta.get("last_sync_at"),
        "last_scan_complete": json.loads(meta.get("last_scan_complete", "false")),
        "compatible_with_requested_model": meta.get("index_signature") == expected_signature,
    }


def clean_excerpt(text: str, limit: int = 260) -> str:
    text = " ".join(text.split())
    text = "".join(character for character in text if character.isprintable())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def clean_label(value: str, limit: int = 200) -> str:
    return clean_excerpt(value, limit=limit)


def search_index(args: argparse.Namespace) -> dict[str, Any]:
    query = args.query.strip()
    if not query:
        raise UserError("Search query must not be empty")
    if args.limit < 1 or args.limit > 100:
        raise UserError("--limit must be between 1 and 100")

    db_path = Path(args.db).expanduser()
    connection = connect_database(db_path, create=False)
    try:
        ensure_schema(connection)
        meta = read_meta(connection)
        expected_signature = index_signature(args.model)
        if meta.get("index_signature") != expected_signature:
            raise UserError(
                "The index is incompatible with the requested model or installed fastembed version; run `sync`"
            )
        dimension = int(meta.get("vector_dimension", "0"))
        if dimension <= 0:
            raise UserError("The index contains no searchable note chunks; run `sync` after adding notes")
        rows = connection.execute("""
            SELECT n.account_id, n.note_id, n.account_name, n.folder_path, n.title,
                   n.modified_at, c.ordinal, c.text AS chunk_text, c.vector
            FROM chunks c
            JOIN notes n ON n.account_id = c.account_id AND n.note_id = c.note_id
            ORDER BY n.account_id, n.note_id, c.ordinal
            """).fetchall()
    finally:
        connection.close()
    if not rows:
        raise UserError("The index contains no searchable note chunks; run `sync` after adding notes")

    model = load_embedding_model(args.model, Path(args.cache_dir).expanduser(), args.offline)
    query_vectors = call_embed(model, "query_embed", [query])
    query_blobs, query_dimension = normalize_vectors(query_vectors)
    if len(query_blobs) != 1 or query_dimension != dimension:
        raise UserError("Query vector dimensions do not match the index; run `sync`")

    try:
        import numpy as np
    except ImportError as error:
        raise UserError("numpy is unavailable; run this script with uv or install its inline dependencies") from error

    vectors = []
    expected_bytes = dimension * 4
    for row in rows:
        blob = row["vector"]
        if len(blob) != expected_bytes:
            raise UserError("The index contains a malformed vector; run `rebuild`")
        vector = np.frombuffer(blob, dtype="<f4")
        if not np.all(np.isfinite(vector)):
            raise UserError("The index contains a non-finite vector; run `rebuild`")
        vectors.append(vector)
    matrix = np.vstack(vectors)
    query_vector = np.frombuffer(query_blobs[0], dtype="<f4")
    scores = matrix @ query_vector

    best_by_note: dict[tuple[str, str], dict[str, Any]] = {}
    for row, score_value in zip(rows, scores):
        score = float(score_value)
        identity = (row["account_id"], row["note_id"])
        current = best_by_note.get(identity)
        if current is None or score > current["score"]:
            best_by_note[identity] = {
                "account_id": row["account_id"],
                "note_id": row["note_id"],
                "title": row["title"],
                "account": row["account_name"],
                "folder": row["folder_path"],
                "modified_at": row["modified_at"],
                "score": score,
                "excerpt": clean_excerpt(row["chunk_text"]),
            }

    results = sorted(
        best_by_note.values(),
        key=lambda result: (-result["score"], result["title"].casefold(), result["note_id"]),
    )[: args.limit]
    return {"ok": True, "command": "search", "query": query, "count": len(results), "results": results}


def open_note(args: argparse.Namespace) -> dict[str, Any]:
    identifier = args.identifier.strip()
    if not identifier or any(ord(character) < 32 for character in identifier):
        raise UserError("Note ID must not be empty or contain control characters")
    connection = connect_database(Path(args.db).expanduser(), create=False)
    try:
        ensure_schema(connection)
        rows = connection.execute("SELECT account_id, note_id, title FROM notes").fetchall()
    finally:
        connection.close()
    matches = [row for row in rows if row["note_id"] == identifier or row["note_id"].startswith(identifier)]
    if not matches:
        raise UserError(f"No indexed note matches ID {identifier!r}")
    if len(matches) > 1:
        raise UserError(f"Note ID prefix {identifier!r} is ambiguous")
    match = matches[0]
    try:
        completed = subprocess.run(
            [
                "/usr/bin/osascript",
                "-l",
                "JavaScript",
                "-e",
                JXA_OPEN_NOTE,
                match["account_id"],
                match["note_id"],
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        response = json.loads(completed.stdout.strip())
    except (subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise UserError(f"Could not open note: {error}") from error
    if not response.get("ok"):
        raise UserError(response.get("error", "Apple Notes could not open the note"))
    return {"ok": True, "command": "open", "note_id": match["note_id"], "title": match["title"]}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help=f"Index database (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"FastEmbed model (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--cache-dir", default=str(DEFAULT_CACHE_DIR), help=f"Embedding model cache (default: {DEFAULT_CACHE_DIR})"
    )
    parser.add_argument("--offline", action="store_true", help="Use only an already-cached embedding model")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    commands = parser.add_subparsers(dest="command", required=True)
    sync_parser = commands.add_parser("sync", help="Incrementally update the local index")
    sync_parser.add_argument(
        "--include-locked",
        action="store_true",
        help="Index password-protected notes when Notes currently exposes their plaintext",
    )
    rebuild_parser = commands.add_parser("rebuild", help="Atomically re-embed all currently visible notes")
    rebuild_parser.add_argument(
        "--include-locked",
        action="store_true",
        help="Index password-protected notes when Notes currently exposes their plaintext",
    )
    search_parser = commands.add_parser("search", help="Semantically search the local index")
    search_parser.add_argument("query", help="Natural-language search query")
    search_parser.add_argument("-n", "--limit", type=int, default=10, help="Maximum matching notes (default: 10)")
    commands.add_parser("status", help="Show local index status without loading the model")
    open_parser = commands.add_parser("open", help="Open an indexed note in Apple Notes")
    open_parser.add_argument("identifier", help="Full note ID or an unambiguous ID prefix from search output")
    return parser


def print_human(result: dict[str, Any]) -> None:
    command = result["command"]
    if command == "search":
        for index, item in enumerate(result["results"], 1):
            location = " / ".join(clean_label(part) for part in (item["account"], item["folder"]) if part)
            details = f"score {item['score']:.3f}"
            if location:
                details += f" · {location}"
            if item["modified_at"]:
                details += f" · {item['modified_at']}"
            print(
                f"{index}. {clean_label(item['title'])}\n   {details}\n   {item['excerpt']}\n"
                f"   id: {clean_label(item['note_id'])}"
            )
        if not result["results"]:
            print("No matching notes.")
    elif command in ("sync", "rebuild"):
        print(
            f"{command.capitalize()} complete: {result['notes_seen']} notes seen, "
            f"{result['notes_reindexed']} reindexed, {result['notes_deleted']} deleted, "
            f"{result['notes_excluded']} excluded, {result['chunks_embedded']} chunks embedded."
        )
        if not result["scan_complete"]:
            print(
                "Warning: the scan was incomplete, so missing notes were not deleted from the index.", file=sys.stderr
            )
        for error in result["scan_errors"]:
            print(f"Warning: {json.dumps(error, ensure_ascii=False)}", file=sys.stderr)
    elif command == "status":
        print(f"Database: {result['database']}")
        print(f"Model: {result['model'] or 'not set'}")
        print(f"Notes: {result['notes']} ({result['searchable_notes']} searchable, {result['locked_notes']} locked)")
        print(f"Chunks: {result['chunks']}")
        print(f"Last sync: {result['last_sync_at'] or 'never'}")
        print(f"Compatible: {'yes' if result['compatible_with_requested_model'] else 'no; run sync'}")
    elif command == "open":
        print(f"Opened {clean_label(result['title'])} ({clean_label(result['note_id'])})")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "sync":
            result = sync_index(args)
        elif args.command == "rebuild":
            result = sync_index(args, force=True)
        elif args.command == "search":
            result = search_index(args)
        elif args.command == "status":
            result = status_index(args)
        elif args.command == "open":
            result = open_note(args)
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2
    except (UserError, sqlite3.Error, OSError) as error:
        if args.json:
            print(json.dumps({"ok": False, "command": args.command, "error": str(error)}, ensure_ascii=False))
        else:
            print(f"Error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
