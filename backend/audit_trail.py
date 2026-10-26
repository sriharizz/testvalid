import json
import hashlib
import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
from schemas import AuditLogEntry

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
ARCHIVE_DIR = ARTIFACTS_DIR / "archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

GENESIS_HASH = "0" * 64

class AuditTrailManager:
    """
    Append-Only, Hash-Chained Audit Trail Manager.
    Complies with FDA 21 CFR Part 11 (§ 11.10(e)) and ISPE GAMP 5 ALCOA+ data integrity rules.
    Every event is cryptographically sealed to its predecessor via SHA-256 hash chaining.
    """

    @staticmethod
    def get_audit_file_path(session_id: str) -> Path:
        session_dir = ARCHIVE_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir / "audit_trail.jsonl"

    @classmethod
    def log_event(
        cls,
        session_id: str,
        actor_username: str,
        actor_role: str,
        event_type: str,
        details: str,
        step_id: Optional[str] = None,
        justification: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Appends a cryptographically chained GxP audit log entry.
        """
        audit_file = cls.get_audit_file_path(session_id)
        
        sequence_no = 1
        prev_hash = GENESIS_HASH

        # Read last entry to determine next sequence_no and prev_hash
        if audit_file.exists() and audit_file.stat().st_size > 0:
            try:
                with open(audit_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if lines:
                        last_line = json.loads(lines[-1])
                        sequence_no = last_line.get("sequence_no", len(lines)) + 1
                        prev_hash = last_line.get("entry_hash", GENESIS_HASH)
            except Exception as e:
                print(f"[AuditTrail] Warning reading last entry from {audit_file}: {e}")

        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Compute tamper-evident SHA-256 hash
        payload = f"{sequence_no}|{now_utc}|{session_id}|{actor_username}|{event_type}|{details}|{prev_hash}"
        entry_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        entry = AuditLogEntry(
            sequence_no=sequence_no,
            timestamp_utc=now_utc,
            session_id=session_id,
            actor_username=actor_username or "system",
            actor_role=actor_role or "SYSTEM",
            event_type=event_type,
            step_id=step_id,
            details=details,
            justification=justification,
            prev_hash=prev_hash,
            entry_hash=entry_hash
        )

        with open(audit_file, "a", encoding="utf-8") as f:
            f.write(entry.model_dump_json() + "\n")

        return entry

    @classmethod
    def get_audit_trail(cls, session_id: str) -> List[AuditLogEntry]:
        """Returns all audit log entries for a given session."""
        audit_file = cls.get_audit_file_path(session_id)
        entries: List[AuditLogEntry] = []
        if not audit_file.exists():
            return entries

        with open(audit_file, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str:
                    try:
                        entries.append(AuditLogEntry.model_validate_json(line_str))
                    except Exception as e:
                        print(f"[AuditTrail] Error parsing entry: {e}")
        return entries

    @classmethod
    def verify_audit_trail(cls, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Cryptographically validates the entire SHA-256 hash chain.
        Returns: (is_valid: bool, error_message: Optional[str])
        """
        audit_file = cls.get_audit_file_path(session_id)
        if not audit_file.exists():
            return True, None

        expected_prev = GENESIS_HASH
        expected_seq = 1

        with open(audit_file, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue
                try:
                    entry = json.loads(line_str)
                except Exception as e:
                    return False, f"Line {line_idx}: Invalid JSON: {e}"

                seq = entry.get("sequence_no")
                if seq != expected_seq:
                    return False, f"Line {line_idx}: Broken sequence: expected {expected_seq}, got {seq}"

                prev_hash = entry.get("prev_hash")
                if prev_hash != expected_prev:
                    return False, f"Line {line_idx}: Broken hash chain: expected prev_hash '{expected_prev}', got '{prev_hash}'"

                # Recompute hash
                payload = f"{seq}|{entry.get('timestamp_utc')}|{entry.get('session_id')}|{entry.get('actor_username')}|{entry.get('event_type')}|{entry.get('details')}|{prev_hash}"
                expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                actual_hash = entry.get("entry_hash")

                if actual_hash != expected_hash:
                    return False, f"Line {line_idx}: Tampering detected: entry_hash mismatch (expected '{expected_hash}', got '{actual_hash}')"

                expected_prev = actual_hash
                expected_seq += 1

        return True, None
