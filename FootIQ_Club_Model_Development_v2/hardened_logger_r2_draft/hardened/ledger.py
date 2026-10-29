"""Append-only, hash-chained, atomically written ledger with external anchor.

Layout (root = ledger directory, anchor = file kept OUTSIDE the root, ideally on another drive and copied to the owner's records):
  root/batches/B000001__<batch_id>.jsonl   first line = header (batch_seq, prev_batch_sha256, n_records, record_sha256 list), then one sealed record per line; read-only
  root/pending/<batch_id>.intent.json      write-ahead intent for an interrupted run (removed when the batch is committed and anchored)
  anchor/anchor.jsonl                      one line per committed batch (seq, batch_sha256) - detects deletion of the newest batch
Verification fails on: temp/orphan files, pending intents, non-contiguous or reordered batches, broken prev-hash chain, header/record mismatch, duplicate (fixture, model) keys,
anchor entry without batch (deleted newest batch), batch without anchor entry (unanchored / interrupted)."""
import hashlib
import json
import os
import re
import stat
import time

BATCH_RE = re.compile(r"^B(\d{6})__(.+)\.jsonl$")


class LedgerError(RuntimeError):
    pass


class SimulatedCrash(RuntimeError):
    pass


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def canon(rec) -> str:
    return json.dumps(rec, sort_keys=True, default=str, ensure_ascii=False)


def utc_now_str() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class ChainedLedger:
    def __init__(self, root: str, anchor_path: str, key_fields=("fixture_id", "model_key")):
        self.root, self.anchor_path, self.key_fields = root, anchor_path, key_fields
        self.bdir, self.pdir = os.path.join(root, "batches"), os.path.join(root, "pending")
        self.lock = os.path.join(root, "ledger.lock")

    # ---------------------------------------------------------------- read side
    def _batch_files(self):
        if not os.path.isdir(self.bdir):
            return []
        return sorted(f for f in os.listdir(self.bdir))

    def _anchor_entries(self):
        if not os.path.exists(self.anchor_path):
            return []
        out = []
        with open(self.anchor_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    out.append(json.loads(line))
        return out

    def verify(self, require_anchor=True) -> dict:
        errors, records, prev, seqs = [], [], "GENESIS", []
        files = self._batch_files()
        for f in files:
            m = BATCH_RE.match(f)
            if not m:
                errors.append(f"unexpected or temporary file in batches/: {f}")
        good = [f for f in files if BATCH_RE.match(f)]
        for i, f in enumerate(good, start=1):
            m = BATCH_RE.match(f)
            seq = int(m.group(1)); seqs.append(seq)
            if seq != i:
                errors.append(f"batch sequence not contiguous at {f} (expected B{i:06d})")
            path = os.path.join(self.bdir, f)
            raw = open(path, "rb").read()
            lines = [l for l in raw.decode("utf-8").split("\n") if l.strip()]
            try:
                header = json.loads(lines[0]); recs = [json.loads(l) for l in lines[1:]]
            except Exception:
                errors.append(f"unreadable or partially written batch: {f}"); continue
            if header.get("type") != "header" or header.get("batch_seq") != seq:
                errors.append(f"header/sequence mismatch in {f}")
            if header.get("prev_batch_sha256") != prev:
                errors.append(f"hash chain broken at {f}")
            if header.get("n_records") != len(recs) or header.get("record_sha256") != [sha_bytes(canon(r).encode()) for r in recs]:
                errors.append(f"records do not match header (partial write or tampering): {f}")
            prev = sha_bytes(raw)
            records += recs
        keys = [tuple(r.get(k) for k in self.key_fields) for r in records]
        if len(keys) != len(set(keys)):
            errors.append("duplicate (fixture, model) key sealed more than once")
        if os.path.isdir(self.pdir):
            for f in os.listdir(self.pdir):
                errors.append(f"pending write-ahead intent (interrupted run): {f}")
        if require_anchor:
            anc = self._anchor_entries()
            hashes = {}
            p2 = "GENESIS"
            for f in good:
                raw = open(os.path.join(self.bdir, f), "rb").read(); hashes[int(BATCH_RE.match(f).group(1))] = sha_bytes(raw)
            for a in anc:
                s = a["batch_seq"]
                if s not in hashes:
                    errors.append(f"anchor lists batch {s} that is missing from the ledger (deleted batch)")
                elif hashes[s] != a["batch_sha256"]:
                    errors.append(f"batch {s} differs from its anchor entry")
            anchored = {a["batch_seq"] for a in anc}
            for s in hashes:
                if s not in anchored:
                    errors.append(f"batch {s} is not anchored (interrupted run or tampering)")
            if [a["batch_seq"] for a in anc] != sorted(anchored) or len(anc) != len(anchored):
                errors.append("anchor entries out of order or duplicated")
        return dict(ok=not errors, errors=errors, batches=len(good), records=len(records), last_batch_sha256=prev, sealed_keys={k for k in keys})

    def records(self):
        out = []
        for f in self._batch_files():
            if BATCH_RE.match(f):
                lines = [l for l in open(os.path.join(self.bdir, f), encoding="utf-8").read().split("\n") if l.strip()]
                out += [json.loads(l) for l in lines[1:]]
        return out

    # ---------------------------------------------------------------- write side
    def _acquire(self):
        os.makedirs(self.root, exist_ok=True)
        try:
            fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.write(fd, str(os.getpid()).encode()); os.close(fd)
        except FileExistsError:
            raise LedgerError("ledger is locked by another process (or a crashed run left ledger.lock): resolve manually")

    def _release(self):
        try:
            os.remove(self.lock)
        except OSError:
            pass

    def append_batch(self, records, batch_id, header_extra=None, _crash_after=None):
        """Idempotent: records whose (fixture, model) key is already sealed are skipped. Returns dict(path, sha256, sealed, skipped)."""
        self._acquire()
        try:
            v = self.verify()
            if not v["ok"]:
                raise LedgerError("ledger failed verification before writing: " + "; ".join(v["errors"][:4]))
            sealed = v["sealed_keys"]
            new, skipped = [], []
            for r in records:
                k = tuple(r.get(x) for x in self.key_fields)
                (skipped if k in sealed else new).append(r)
                sealed = sealed | {k}
            if not new:
                return dict(path=None, sha256=None, sealed=0, skipped=len(skipped))
            seq = v["batches"] + 1
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", batch_id)
            final = os.path.join(self.bdir, f"B{seq:06d}__{safe}.jsonl"); tmp = final + ".tmp"
            header = dict(type="header", batch_seq=seq, batch_id=batch_id, prev_batch_sha256=v["last_batch_sha256"], n_records=len(new), record_sha256=[sha_bytes(canon(r).encode()) for r in new], created_utc=utc_now_str(), extra=header_extra or {})
            body = (canon(header) + "\n" + "".join(canon(r) + "\n" for r in new)).encode("utf-8")
            os.makedirs(self.bdir, exist_ok=True); os.makedirs(self.pdir, exist_ok=True); os.makedirs(os.path.dirname(self.anchor_path), exist_ok=True)
            intent = os.path.join(self.pdir, safe + ".intent.json")
            with open(intent, "w", encoding="utf-8") as fh:
                json.dump(dict(batch_seq=seq, batch_id=batch_id, final=final, expected_sha256=sha_bytes(body), n_records=len(new)), fh); fh.flush(); os.fsync(fh.fileno())
            if _crash_after == "intent": raise SimulatedCrash("after intent")
            with open(tmp, "wb") as fh:
                fh.write(body[: len(body) // 2] if _crash_after == "partial" else body); fh.flush(); os.fsync(fh.fileno())
            if _crash_after in ("tmp", "partial"): raise SimulatedCrash("after tmp write")
            os.replace(tmp, final)
            os.chmod(final, stat.S_IREAD)
            if _crash_after == "rename": raise SimulatedCrash("after rename, before anchor")
            self._anchor(seq, sha_bytes(body), batch_id, len(new))
            os.remove(intent)
            return dict(path=final, sha256=sha_bytes(body), sealed=len(new), skipped=len(skipped), batch_seq=seq)
        finally:
            self._release()

    def _anchor(self, seq, sha, batch_id, n):
        with open(self.anchor_path, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(dict(batch_seq=seq, batch_sha256=sha, batch_id=batch_id, records=n, anchored_utc=utc_now_str())) + "\n"); fh.flush(); os.fsync(fh.fileno())

    def recover(self):
        """Resolve interrupted runs. A committed batch (final file with the intended hash) is anchored and completed; anything else is discarded (nothing was sealed)."""
        actions = []
        if os.path.exists(self.lock):
            os.remove(self.lock); actions.append("removed stale lock")
        if not os.path.isdir(self.pdir):
            return actions
        for f in sorted(os.listdir(self.pdir)):
            it = json.load(open(os.path.join(self.pdir, f), encoding="utf-8"))
            final, tmp = it["final"], it["final"] + ".tmp"
            if os.path.exists(final) and sha_bytes(open(final, "rb").read()) == it["expected_sha256"]:
                if not any(a["batch_seq"] == it["batch_seq"] for a in self._anchor_entries()):
                    self._anchor(it["batch_seq"], it["expected_sha256"], it["batch_id"], it["n_records"]); actions.append(f"anchored committed batch {it['batch_seq']}")
                else:
                    actions.append(f"batch {it['batch_seq']} already anchored")
            else:
                if os.path.exists(tmp): os.remove(tmp); actions.append(f"discarded partial/uncommitted temp for batch {it['batch_seq']}")
                else: actions.append(f"intent for batch {it['batch_seq']} had no data")
            os.remove(os.path.join(self.pdir, f))
        return actions
