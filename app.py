"""
app.py  —  VChat Web Converter
Upload a WhatsApp export .zip → view in browser → download self-contained .html
"""
import base64
import io
import json
import logging
import os
import re
import zipfile
import secrets
from datetime import datetime
from pathlib import Path

from collections import namedtuple

from flask import Flask, jsonify, render_template, request, session, abort, Response
from werkzeug.utils import secure_filename

# ── App setup ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200 MB hard limit
app.secret_key = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ── Supported media types ──────────────────────────────────────────────────────
AUDIO_EXTS = {".opus", ".mp3", ".m4a", ".aac", ".ogg", ".wav"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".3gp", ".webm"}

# ── Parser: multiple regex patterns with fallback chain (Fix #1) ───────────────
# Pattern 1: Android 12hr  — 03/04/26, 3:22 PM - Sender: msg
_P1 = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2}\s*[AP]M)\s*[-\u2013]\s*([^:]+?):\s*(.+)$", re.I)
# Pattern 2: Android 24hr  — 03/04/2026, 15:22 - Sender: msg
_P2 = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}),\s*(\d{1,2}:\d{2})\s*[-\u2013]\s*([^:]+?):\s*(.+)$")
_P3 = re.compile(r"^\[(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\s*,?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\]\s*([^:]+?):\s*(.+)$", re.I)
# Pattern 4: dot separator — 03.04.2026, 15:22 - Sender: msg
_P4 = re.compile(r"^(\d{1,2}\.\d{1,2}\.\d{2,4}),\s*(\d{1,2}:\d{2})\s*[-\u2013]\s*([^:]+?):\s*(.+)$")
# Pattern 5: dash/space/hyphen formats — 28-07-2026 14:30 - Sender: msg
_P5 = re.compile(r"^(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})\s*,?\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AP]M)?)\s*[-\u2013]\s*([^:]+?):\s*(.+)$", re.I)

PATTERNS = [_P1, _P2, _P3, _P4, _P5]

# Attachment line - general extension-based heuristic (locale independent)
_ATTACH_RE = re.compile(r"^(\S.+\.[a-zA-Z0-9]{2,6})\s*\(([^)]+)\)$", re.IGNORECASE)


def _should_skip_content(content: str) -> bool:
    """Helper to detect omitted media and deleted messages in any language."""
    content_lower = content.lower()
    # Omitted media
    if (content.startswith("<") and content.endswith(">")) or (content.startswith("[") and content.endswith("]")):
        if any(w in content_lower for w in ("omit", "excl", "media", "multimedia", "omiss", "medien", "schloss")):
            return True
    # Deleted messages
    if any(w in content_lower for w in ("deleted", "eliminad", "gelöscht", "supprimé", "apagad")):
        return True
    if content_lower == "null":
        return True
    return False


def _match_line(line: str):
    """Try all patterns. Returns (date_str, time_str, sender, content) or None."""
    line = line.strip()
    # Strip invisible unicode (narrow no-break space, BOM, RLM, LRM)
    line = re.sub(r"[\u200e\u200f\u202a-\u202e\ufeff]", "", line)
    for pat in PATTERNS:
        m = pat.match(line)
        if m:
            return m.group(1), m.group(2), m.group(3).strip(), m.group(4).strip()
    return None


def _parse_dt(date_str: str, time_str: str) -> datetime:
    """Parse date+time string — handles 12hr/24hr, 2-digit/4-digit year."""
    # Normalise unicode spaces and separators
    date_str = date_str.replace(".", "/").strip()
    time_str = re.sub(r"[\u202f\xa0]", " ", time_str).strip().upper()

    parts = date_str.split("/")
    if len(parts[2]) == 2:
        parts[2] = "20" + parts[2]
    date_str = "/".join(parts)

    fmts_12 = ["%d/%m/%Y %I:%M %p", "%m/%d/%Y %I:%M %p", "%d/%m/%Y %I:%M:%S %p"]
    fmts_24 = ["%d/%m/%Y %H:%M",    "%m/%d/%Y %H:%M",    "%d/%m/%Y %H:%M:%S"]
    fmts = (fmts_12 if re.search(r"[AP]M$", time_str) else fmts_24)

    for fmt in fmts:
        try:
            return datetime.strptime(f"{date_str} {time_str}", fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: '{date_str} {time_str}'")


def _audio_duration(audio_bytes: bytes) -> int:
    try:
        from mutagen import File as MutagenFile
        tag = MutagenFile(io.BytesIO(audio_bytes))
        if tag and tag.info:
            return round(tag.info.length)
    except Exception as e:
        log.debug("mutagen duration extraction failed: %s", e)
    return 0


def _validate_zip(zip_bytes: bytes) -> None:
    """Raise ValueError for corrupted or obviously malicious ZIPs."""
    if len(zip_bytes) < 4:
        raise ValueError("File is too small to be a valid ZIP.")
    if zip_bytes[:2] != b"PK":
        raise ValueError("File is not a valid ZIP archive.")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            bad = zf.testzip()
            if bad:
                raise ValueError(f"Corrupted entry in ZIP: {bad}")
    except zipfile.BadZipFile as e:
        raise ValueError(f"Invalid ZIP file: {e}") from e
# ── Core parser (Fix #1 — multi-line stitching) ───────────────────────────────
def parse_whatsapp_txt(txt: str, chat_name: str) -> list[dict]:
    """
    Parse WhatsApp export text into a list of message dicts.
    Multi-line messages are stitched to their parent message.
    System messages and skipped content are filtered out.
    """
    raw_lines = txt.splitlines()
    # Step 1: group physical lines into logical messages
    logical: list[tuple[str, str, str, str]] = []  # (date, time, sender, content)
    unparsed_lines_count = 0
    for line in raw_lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        parsed = _match_line(line)
        if parsed:
            logical.append(list(parsed))
        elif logical:
            # Continuation line — append to previous message content (Fix #1)
            logical[-1][3] += "\n" + line_stripped
        else:
            # Non-empty line that doesn't match a message header and has no parent message to append to
            unparsed_lines_count += 1

    if unparsed_lines_count > 0:
        log.warning("Skipped %d unparsed non-empty lines before the first logical chat message.", unparsed_lines_count)

    messages = []
    msg_id = 1

    for date_str, time_str, sender, content in logical:
        # Skip system messages (no colon separator = no sender in original line)
        if not sender:
            continue
        try:
            dt = _parse_dt(date_str, time_str)
        except (ValueError, IndexError) as e:
            log.debug("Skipping unparseable timestamp: %s", e)
            continue

        timestamp = dt.strftime("%Y-%m-%dT%H:%M:%S")
        content = content.strip()

        # Skip deleted / omitted
        if not content or _should_skip_content(content):
            continue
        if content.startswith("\u202e"):  # RTL override — skip system msgs
            continue

        # Check if this is a reaction to the previous message
        react_match = re.match(r"^reacted\s+with\s+(.+)$", content, re.I)
        if react_match and messages:
            emoji = react_match.group(1).strip().strip('"\'')
            prev_msg = messages[-1]
            if "reactions" not in prev_msg:
                prev_msg["reactions"] = []
            # Check if this sender already reacted, if so update it
            existing = next((r for r in prev_msg["reactions"] if r["sender"] == sender), None)
            if existing:
                existing["emoji"] = emoji
            else:
                prev_msg["reactions"].append({"sender": sender, "emoji": emoji})
            continue # Do not add reaction as separate message row

        # Split logical content into first line (attachment) and subsequent lines (caption)
        lines = content.splitlines()
        first_line = lines[0].strip() if lines else ""
        caption = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        attach = _ATTACH_RE.match(first_line)
        if attach:
            fname = attach.group(1).strip()
            ext   = Path(fname).suffix.lower()
            if ext in AUDIO_EXTS:
                messages.append({
                    "id": msg_id, "type": "audio", "sender": sender,
                    "timestamp": timestamp,
                    "audio_file": f"voice_notes/{fname}", "duration_seconds": 0
                })
            elif ext in IMAGE_EXTS:
                messages.append({
                    "id": msg_id, "type": "image", "sender": sender,
                    "timestamp": timestamp,
                    "media_file": f"media/{fname}", "caption": caption
                })
            elif ext in VIDEO_EXTS:
                messages.append({
                    "id": msg_id, "type": "video", "sender": sender,
                    "timestamp": timestamp,
                    "media_file": f"media/{fname}", "caption": caption
                })
            else:
                # Other attachments (pdf, docx, etc.) — show as file
                messages.append({
                    "id": msg_id, "type": "file", "sender": sender,
                    "timestamp": timestamp,
                    "filename": fname
                })
        else:
            messages.append({
                "id": msg_id, "type": "text", "sender": sender,
                "timestamp": timestamp, "content": content
            })
        msg_id += 1

    return messages


# ── Convert WhatsApp ZIP → manifest + media ───────────────────────────────────
ConvertResult = namedtuple("ConvertResult", ["manifest", "opus_map", "image_map", "video_map", "missing_media"])


def convert_zip(zip_bytes: bytes) -> ConvertResult:
    _validate_zip(zip_bytes)  # Fix #2 — validate before processing

    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as wz:
        names = wz.namelist()

        # Fix #2 — reject zip bombs / suspiciously large entries
        total_uncompressed = sum(i.file_size for i in wz.infolist())
        if total_uncompressed > 1 * 1024 ** 3:  # 1 GB uncompressed limit
            raise ValueError("ZIP contents exceed 1 GB uncompressed limit.")

        txt_name = next((n for n in names if n.endswith(".txt")), None)
        if not txt_name:
            raise ValueError("No .txt chat file found inside the ZIP.")

        txt = wz.read(txt_name).decode("utf-8", errors="replace")
        chat_name = Path(txt_name).stem

        messages = parse_whatsapp_txt(txt, chat_name)
        if not messages:
            raise ValueError("No messages could be parsed from the chat file. "
                             "The export format may not be supported.")

        participants = list(dict.fromkeys(m["sender"] for m in messages))

        # Build lookup maps (Fix #2 — handle missing media gracefully)
        # Keys are sanitized filenames to match against sanitized fnames from chat text
        opus_map  = {secure_filename(Path(n).name): n for n in names if Path(n).suffix.lower() in AUDIO_EXTS}
        image_map = {secure_filename(Path(n).name): n for n in names if Path(n).suffix.lower() in IMAGE_EXTS}
        video_map = {secure_filename(Path(n).name): n for n in names if Path(n).suffix.lower() in VIDEO_EXTS}

        missing_media: list[str] = []

        for msg in messages:
            if msg["type"] == "audio":
                fname = secure_filename(Path(msg["audio_file"]).name)
                if fname in opus_map:
                    ab = wz.read(opus_map[fname])
                    msg["duration_seconds"] = _audio_duration(ab)
                else:
                    missing_media.append(fname)
                    msg["missing"] = True
            elif msg["type"] == "image":
                fname = secure_filename(Path(msg["media_file"]).name)
                if fname in image_map:
                    info = wz.getinfo(image_map[fname])
                    if info.file_size > 30 * 1024 * 1024:
                        msg["too_large"] = True
                else:
                    missing_media.append(fname)
                    msg["missing"] = True
            elif msg["type"] == "video":
                fname = secure_filename(Path(msg["media_file"]).name)
                if fname in video_map:
                    info = wz.getinfo(video_map[fname])
                    if info.file_size > 30 * 1024 * 1024:
                        msg["too_large"] = True
                else:
                    missing_media.append(fname)
                    msg["missing"] = True

        manifest = {
            "version": "1.0",
            "chat_name": chat_name,
            "participants": participants,
            "messages": messages
        }

        if missing_media:
            log.info("Missing media files (%d): %s", len(missing_media), missing_media[:5])

        return ConvertResult(manifest, opus_map, image_map, video_map, missing_media)


def convert_txt(txt_bytes: bytes, filename: str) -> ConvertResult:
    txt = txt_bytes.decode("utf-8", errors="replace")
    chat_name = Path(filename).stem

    messages = parse_whatsapp_txt(txt, chat_name)
    if not messages:
        raise ValueError("No messages could be parsed from the chat file. "
                         "The export format may not be supported.")

    participants = list(dict.fromkeys(m["sender"] for m in messages))
    missing_media: list[str] = []

    for msg in messages:
        if msg["type"] == "audio":
            msg["missing"] = True
            fname = secure_filename(Path(msg["audio_file"]).name)
            missing_media.append(fname)
        elif msg["type"] == "image":
            msg["missing"] = True
            fname = secure_filename(Path(msg["media_file"]).name)
            missing_media.append(fname)
        elif msg["type"] == "video":
            msg["missing"] = True
            fname = secure_filename(Path(msg["media_file"]).name)
            missing_media.append(fname)

    manifest = {
        "version": "1.0",
        "chat_name": chat_name,
        "participants": participants,
        "messages": messages
    }

    return ConvertResult(manifest, {}, {}, {}, missing_media)


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/convert", methods=["POST"])
def convert():
    # Fix #4 — validate file presence and type
    if "zipfile" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    f = request.files["zipfile"]
    if not f.filename:
        return jsonify({"error": "Empty filename."}), 400

    raw = f.read()

    # Determine parser based on file type
    is_zip = raw[:2] == b"PK"
    is_txt = f.filename.lower().endswith(".txt")

    if not is_zip and not is_txt:
        return jsonify({"error": "Uploaded file must be a .zip or a .txt file."}), 400

    try:
        if is_zip:
            result = convert_zip(raw)
        else:
            result = convert_txt(raw, f.filename)
        manifest, missing = result.manifest, result.missing_media
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        log.exception("Unexpected conversion error")
        return jsonify({"error": "Conversion failed. Check the server logs."}), 500

    safe_name = secure_filename(manifest["chat_name"]) or "chat"

    return jsonify({
        "manifest": manifest,
        "filename": f"{safe_name}.html",
        "warnings": {"missing_media": len(missing)}
    })


# Fix #4 — disable debug via env var, never hardcode
if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, port=5000)
