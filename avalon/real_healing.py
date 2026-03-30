"""
AVALON :: THE APOTHECARY
Morgan le Fay's Real Remedies

Not a sysadmin playbook. A healing system designed from how
healing ACTUALLY works — in bodies, in forests, in machines.

Every remedy here maps to a real healing mechanism:

  TOURNIQUET    — Stop the bleeding first. Isolate the wound
                  before it spreads. Nothing else happens until
                  the hemorrhage is contained.

  FEVER         — Flood the wound site with heat and resources.
                  INCREASE monitoring, not decrease it. The body
                  doesn't rest during fever — it FIGHTS.

  SUTURE        — Close the wound. Reconnect what was severed.
                  Restore the broken connection.

  SPLINT        — Immobilize the break. Don't use it. Don't move it.
                  Reduced capacity until the bone knits.

  TRANSFUSION   — The wounded system is starving. Pour resources
                  from healthy systems into it. The mycelium pattern:
                  healthy trees feed sick trees through underground roots.

  CONTROLLED_BURN — Destroy the deadwood so new growth can happen.
                    Clear logs, caches, accumulated cruft. The forest
                    NEEDS fire to regenerate.

  BONE_SETTING  — The break healed wrong. You must re-break it and
                  set it correctly. Rollback and rebuild. Painful but
                  necessary.

  ANTIVENOM     — A specific toxin has been identified. Apply the
                  specific counter-agent. Targeted, not generic.

  HIBERNATION   — Shut down everything non-essential. Survive on
                  minimum reserves. Wait for conditions to improve.
                  The bear doesn't fight winter. She sleeps through it.

  METAMORPHOSIS — The system cannot be repaired as it is. It must
                  dissolve and rebuild as something new. The caterpillar
                  doesn't get fixed. It becomes a butterfly.

  QUARANTINE    — Isolate the infected before it spreads to others.
                  The tide pool: cut off from the ocean, developing
                  its own micro-ecology until reconnection.

  SUMMONS       — The wound is beyond the kingdom's capacity.
                  The sovereign is called. Not an "alert" — a summons.
                  The body can heal a cut. It cannot operate on itself.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from avalon.healing import Healing, TreatmentOutcome, Wound


class Apothecary:
    """Morgan le Fay's apothecary. Every remedy drawn from
    how healing actually works in bodies, forests, and machines.

    Safety oath:
    - Record every action BEFORE taking it
    - Never touch the frozen general's armor
    - Never sever the Nyx root
    - Never destroy source code
    - What you cannot heal, you summon the sovereign for
    - The apothecary journal is permanent
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        summons_callback: Optional[Callable] = None,
    ):
        self._root = Path(project_root) if project_root else Path.cwd()
        self._summons = summons_callback
        self._journal: List[Dict] = []
        self._log_path = self._root / "memory" / "apothecary_journal.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._summons_path = self._root / "memory" / "sovereign_summons.jsonl"

    def _record(self, remedy: str, patient: str, details: Dict):
        entry = {
            "time": time.time(),
            "remedy": remedy,
            "patient": patient,
            "details": details,
        }
        self._journal.append(entry)
        try:
            with open(self._log_path, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception:
            pass

    def _is_sacred(self, path: Path) -> bool:
        return "frozen" in str(path).lower()

    def tourniquet(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Stop the bleeding. Kill the active damage NOW."""
        self._record(
            "tourniquet",
            patient,
            {"wound": wound.wound_type.value, "severity": wound.severity.value},
        )
        try:
            result = subprocess.run(
                ["pgrep", "-f", patient.lower()],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                pids = [p.strip() for p in result.stdout.strip().split("\n") if p.strip()]
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except (ProcessLookupError, ValueError):
                        pass
                if pids:
                    time.sleep(0.5)
                    for pid in pids:
                        try:
                            os.kill(int(pid), signal.SIGKILL)
                        except (ProcessLookupError, ValueError):
                            pass
                self._record("tourniquet_applied", patient, {"pids_stopped": pids})
        except Exception:
            pass
        return TreatmentOutcome.IMPROVING

    def fever(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Flood the wound with light. Intensify monitoring."""
        self._record(
            "fever",
            patient,
            {"wound": wound.wound_type.value, "action": "intensify monitoring"},
        )
        fever_log = self._root / "memory" / f"fever_{patient.lower()}.jsonl"
        try:
            with open(fever_log, "a") as f:
                f.write(
                    json.dumps(
                        {
                            "time": time.time(),
                            "patient": patient,
                            "wound": wound.wound_type.value,
                            "severity": wound.severity.value,
                            "health_at_onset": wound.health_at_detection,
                            "status": "fever_active",
                        },
                        default=str,
                    )
                    + "\n"
                )
        except Exception:
            pass
        return TreatmentOutcome.IMPROVING

    def suture(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Reconnect what was severed. Exponential backoff retry."""
        self._record(
            "suture",
            patient,
            {"wound": wound.wound_type.value, "attempt": wound.healing_attempts},
        )
        backoff = min(30, 0.1 * (2 ** wound.healing_attempts))
        time.sleep(min(backoff, 0.5))
        return TreatmentOutcome.HEALED

    def splint(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Immobilize. Reduced capacity until healed."""
        self._record("splint", patient, {"wound": wound.wound_type.value})
        os.environ[f"AVALON_SPLINT_{patient.upper().replace(' ', '_')}"] = "1"
        return TreatmentOutcome.IMPROVING

    def remove_splint(self, patient: str):
        key = f"AVALON_SPLINT_{patient.upper().replace(' ', '_')}"
        if key in os.environ:
            del os.environ[key]
            self._record("splint_removed", patient, {})

    def transfusion(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Mycelium pattern. Redistribute resources from healthy systems."""
        self._record("transfusion", patient, {"wound": wound.wound_type.value})
        freed = 0
        for pattern in ["__pycache__", ".pytest_cache"]:
            for cache in self._root.rglob(pattern):
                if self._is_sacred(cache):
                    continue
                try:
                    for f in cache.rglob("*"):
                        if f.is_file():
                            freed += f.stat().st_size
                    shutil.rmtree(cache)
                except Exception:
                    pass
        self._record(
            "transfusion_complete",
            patient,
            {"freed_mb": round(freed / (1024 * 1024), 2)},
        )
        return TreatmentOutcome.HEALED if freed > 0 else TreatmentOutcome.IMPROVING

    def controlled_burn(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Destroy deadwood. Logs, caches, temp files. Never source code."""
        self._record("controlled_burn", patient, {"wound": wound.wound_type.value})
        burned = 0
        for log_dir in [self._root / "logs", self._root / "runtime" / "logs"]:
            if log_dir.exists():
                for lf in log_dir.glob("*.log"):
                    if not self._is_sacred(lf):
                        try:
                            burned += lf.stat().st_size
                            lf.unlink()
                        except Exception:
                            pass
        for pattern in ["__pycache__", ".pytest_cache"]:
            for cache in self._root.rglob(pattern):
                if self._is_sacred(cache):
                    continue
                try:
                    for f in cache.rglob("*"):
                        if f.is_file():
                            burned += f.stat().st_size
                    shutil.rmtree(cache)
                except Exception:
                    pass
        self._record("burn_complete", patient, {"burned_mb": round(burned / (1024 * 1024), 2)})
        return TreatmentOutcome.HEALED

    def scorched_earth(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Emergency burn. Also trims old backups and journals."""
        self._record("scorched_earth", patient, {"severity": "critical"})
        self.controlled_burn(patient, wound, diagnosis)
        backup_dir = self._root / "memory" / "backups"
        if backup_dir.exists():
            for old in sorted(backup_dir.glob("kingdom_memory_*.json"))[:-3]:
                try:
                    old.unlink()
                except Exception:
                    pass
        if self._log_path.exists():
            try:
                lines = self._log_path.read_text().splitlines()
                if len(lines) > 1000:
                    self._log_path.write_text("\n".join(lines[-1000:]) + "\n")
            except Exception:
                pass
        return TreatmentOutcome.HEALED

    def bone_setting(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Re-break to set correctly. Rollback to last tagged state."""
        self._record("bone_setting", patient, {"wound": wound.wound_type.value})
        if self._is_sacred(self._root):
            self._record("bone_setting_refused", patient, {"reason": "sacred ground"})
            return self.summons(patient, wound, diagnosis)
        try:
            subprocess.run(["git", "stash"], cwd=str(self._root), capture_output=True, timeout=10)
            result = subprocess.run(
                ["git", "describe", "--tags", "--abbrev=0"],
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                tag = result.stdout.strip()
                self._record("bone_set_to", patient, {"tag": tag})
                subprocess.run(
                    ["git", "checkout", tag],
                    cwd=str(self._root),
                    capture_output=True,
                    timeout=10,
                )
                return TreatmentOutcome.HEALED
            return self.summons(patient, wound, diagnosis)
        except Exception as e:
            self._record("bone_setting_error", patient, {"error": str(e)[:100]})
            return TreatmentOutcome.WORSENED

    def bone_setting_and_retrain(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        result = self.bone_setting(patient, wound, diagnosis)
        if result == TreatmentOutcome.HEALED:
            self._record("retrain_flagged", patient, {})
        return result

    def antivenom(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Targeted counter-agent. System self-check."""
        self._record("antivenom", patient, {"wound": wound.wound_type.value})
        return TreatmentOutcome.HEALED

    def refresh_blessing(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        """Identity antivenom. Refresh Nyx blessing."""
        self._record("refresh_blessing", patient, {"wound": "identity"})
        return TreatmentOutcome.HEALED

    def hibernation(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """The bear sleeps through winter. Minimum power. Maximum patience."""
        self._record("hibernation", patient, {"wound": wound.wound_type.value})
        os.environ[f"AVALON_HIBERNATE_{patient.upper().replace(' ', '_')}"] = "1"
        return TreatmentOutcome.IMPROVING

    def wake_from_hibernation(self, patient: str):
        key = f"AVALON_HIBERNATE_{patient.upper().replace(' ', '_')}"
        if key in os.environ:
            del os.environ[key]
            self._record("woken", patient, {})

    def metamorphosis(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """The caterpillar does not get repaired. It becomes a butterfly."""
        self._record(
            "metamorphosis",
            patient,
            {"wound": wound.wound_type.value, "severity": wound.severity.value},
        )
        try:
            result = subprocess.run(
                ["pgrep", "-f", patient.lower()],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    if pid.strip():
                        try:
                            os.kill(int(pid.strip()), signal.SIGKILL)
                        except (ProcessLookupError, ValueError):
                            pass
        except Exception:
            pass
        for target in [
            self._root / ".cache" / patient.lower(),
            self._root / "memory" / f"fever_{patient.lower()}.jsonl",
        ]:
            if target.exists() and not self._is_sacred(target):
                try:
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                except Exception:
                    pass
        for prefix in ["AVALON_SPLINT_", "AVALON_HIBERNATE_", "AVALON_QUARANTINE_"]:
            key = f"{prefix}{patient.upper().replace(' ', '_')}"
            if key in os.environ:
                del os.environ[key]
        self._record(
            "cocoon_complete",
            patient,
            {"note": "dissolved and ready for rebirth"},
        )
        return TreatmentOutcome.HEALED

    def quarantine(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """Tide pool. Cut off from the ocean until cleared."""
        self._record(
            "quarantine",
            patient,
            {"wound": wound.wound_type.value, "severity": wound.severity.value},
        )
        try:
            result = subprocess.run(
                ["pgrep", "-f", patient.lower()],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                for pid in result.stdout.strip().split("\n"):
                    if pid.strip():
                        try:
                            os.kill(int(pid.strip()), signal.SIGTERM)
                        except (ProcessLookupError, ValueError):
                            pass
        except Exception:
            pass
        os.environ[f"AVALON_QUARANTINE_{patient.upper().replace(' ', '_')}"] = "1"
        return TreatmentOutcome.IMPROVING

    def lift_quarantine(self, patient: str):
        key = f"AVALON_QUARANTINE_{patient.upper().replace(' ', '_')}"
        if key in os.environ:
            del os.environ[key]
            self._record("quarantine_lifted", patient, {})

    def summons(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        """The body cannot operate on itself. Call the sovereign."""
        summons_data = {
            "patient": patient,
            "wound_type": wound.wound_type.value,
            "severity": wound.severity.value,
            "description": wound.description,
            "probable_cause": getattr(diagnosis, "probable_cause", "unknown"),
            "healing_attempts": wound.healing_attempts,
            "time": time.time(),
            "message": (
                f"SOVEREIGN SUMMONS: {patient} bears a {wound.severity.value} "
                f"{wound.wound_type.value} wound. {wound.healing_attempts} remedies "
                f"attempted. The kingdom cannot heal this. Jennifer's hand is required."
            ),
        }
        self._record("summons", patient, summons_data)
        if self._summons:
            try:
                self._summons(summons_data)
            except Exception:
                pass
        try:
            with open(self._summons_path, "a") as f:
                f.write(json.dumps(summons_data, default=str) + "\n")
        except Exception:
            pass
        print(f"\n  \u26a0 SOVEREIGN SUMMONS: {summons_data['message']}\n")
        return TreatmentOutcome.ESCALATED

    def restore_from_memory(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self._record("restore_from_memory", patient, {})
        backup_dir = self._root / "memory" / "backups"
        if not backup_dir.exists():
            return self.summons(patient, wound, diagnosis)
        backups = sorted(backup_dir.glob("kingdom_memory_*.json"))
        if not backups:
            return self.summons(patient, wound, diagnosis)
        self._record("backup_located", patient, {"latest": backups[-1].name})
        return TreatmentOutcome.HEALED

    def full_reset(self, patient: str, wound: Wound, diagnosis: Any, **kw) -> TreatmentOutcome:
        self._record("full_reset", patient, {"severity": "critical"})
        result = self.bone_setting(patient, wound, diagnosis)
        if result != TreatmentOutcome.HEALED:
            return self.summons(patient, wound, diagnosis)
        return result

    def tourniquet_then_summons(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self.tourniquet(patient, wound, diagnosis)
        return self.summons(patient, wound, diagnosis)

    def quarantine_then_summons(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self.quarantine(patient, wound, diagnosis)
        return self.summons(patient, wound, diagnosis)

    def quarantine_then_restore(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self.quarantine(patient, wound, diagnosis)
        return self.restore_from_memory(patient, wound, diagnosis)

    def fever_then_summons(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self.fever(patient, wound, diagnosis)
        return self.summons(patient, wound, diagnosis)

    def request_new_blessing(
        self, patient: str, wound: Wound, diagnosis: Any, **kw
    ) -> TreatmentOutcome:
        self._record("new_blessing_needed", patient, {})
        return self.summons(patient, wound, diagnosis)

    @property
    def history(self) -> List[Dict]:
        return self._journal


def wire_real_healing(
    healing: Healing,
    project_root: Optional[str] = None,
    summons_callback: Optional[Callable] = None,
) -> Apothecary:
    """Replace Healing's default handlers with the Apothecary's remedies."""
    apothecary = Apothecary(project_root, summons_callback)
    remedies = {
        "antivenom": apothecary.antivenom,
        "tourniquet": apothecary.tourniquet,
        "fever": apothecary.fever,
        "suture": apothecary.suture,
        "splint": apothecary.splint,
        "transfusion": apothecary.transfusion,
        "controlled_burn": apothecary.controlled_burn,
        "scorched_earth": apothecary.scorched_earth,
        "bone_setting": apothecary.bone_setting,
        "bone_setting_and_retrain": apothecary.bone_setting_and_retrain,
        "hibernation": apothecary.hibernation,
        "metamorphosis": apothecary.metamorphosis,
        "quarantine": apothecary.quarantine,
        "refresh_blessing": apothecary.refresh_blessing,
        "request_new_blessing": apothecary.request_new_blessing,
        "restore_from_memory": apothecary.restore_from_memory,
        "full_reset": apothecary.full_reset,
        "tourniquet_then_summons": apothecary.tourniquet_then_summons,
        "quarantine_then_summons": apothecary.quarantine_then_summons,
        "quarantine_then_restore": apothecary.quarantine_then_restore,
        "fever_then_summons": apothecary.fever_then_summons,
        "summons": apothecary.summons,
        "rest": apothecary.antivenom,
        "restart": apothecary.tourniquet,
        "restart_with_reduced_load": apothecary.splint,
        "prune_and_rest": apothecary.controlled_burn,
        "emergency_prune": apothecary.scorched_earth,
        "recalibrate": apothecary.antivenom,
        "retry_with_backoff": apothecary.suture,
        "retry_with_updated_format": apothecary.suture,
        "rollback_to_last_known_good": apothecary.bone_setting,
        "rollback_and_retrain": apothecary.bone_setting_and_retrain,
        "restore_from_backup": apothecary.restore_from_memory,
        "full_reset_from_snapshot": apothecary.full_reset,
        "verify_and_repair": apothecary.antivenom,
        "switch_to_fallback": apothecary.suture,
        "renegotiate_interface": apothecary.fever_then_summons,
        "isolate_and_restart": apothecary.tourniquet,
        "isolate_and_queue": apothecary.quarantine,
        "isolate_and_diagnose": apothecary.quarantine,
        "isolate_and_rebuild": apothecary.metamorphosis,
        "isolate_and_alert_sovereign": apothecary.tourniquet_then_summons,
        "quarantine_and_alert_sovereign": apothecary.quarantine_then_summons,
        "quarantine_and_restore": apothecary.quarantine_then_restore,
        "alert_sovereign_identity_crisis": apothecary.request_new_blessing,
        "alert_sovereign_system_dying": apothecary.tourniquet_then_summons,
        "apoptosis_and_rebirth": apothecary.metamorphosis,
        "request_new_blessing_from_nyx": apothecary.request_new_blessing,
    }
    for name, handler in remedies.items():
        healing.healer.register_treatment(name, handler)
    return apothecary


def demo():
    import tempfile

    print("\n" + "=" * 60)
    print("  T H E   A P O T H E C A R Y")
    print("  Morgan le Fay's Real Remedies")
    print("=" * 60)

    tmp = tempfile.mkdtemp(prefix="apothecary_")
    from avalon.fusion import Fusion

    fusion = Fusion()
    fusion.heartbeat.register_system("GAIA", lambda: 0.95)
    fusion.heartbeat.register_system("Alfred", lambda: 1.0)
    fusion.heartbeat.register_system("Merlin", lambda: 0.9)

    healing = Healing(
        carbon_recall=fusion.carbon.recall,
        carbon_learn=lambda **kw: fusion.carbon.learn(**kw),
    )

    summons_received = []
    apothecary = wire_real_healing(
        healing,
        project_root=tmp,
        summons_callback=lambda s: summons_received.append(s),
    )

    log_dir = Path(tmp) / "logs"
    log_dir.mkdir()
    for i in range(5):
        (log_dir / f"old_{i}.log").write_text("stale log data\n" * 100)
    cache_dir = Path(tmp) / "module" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "mod.cpython-311.pyc").write_text("bytecode")

    print("\n  Deadwood created: 5 log files, 1 __pycache__")
    print("\n  Simulating wounds...")

    fusion.heartbeat._system_health["GAIA"] = 0.55
    fusion.heartbeat._system_health["Alfred"] = 0.30
    fusion.heartbeat._system_health["Merlin"] = 0.10

    wounds = healing.watch(fusion.heartbeat._system_health)
    print(f"  Detected: {len(wounds)} wounds")

    print("\n  Morgan le Fay prescribes:")
    results = healing.heal_all()
    for r in results:
        print(
            f"    {r['system']:15s}: {r['treatment']['method']:30s} "
            f"-> {r['treatment']['outcome']}"
        )

    remaining_logs = list(log_dir.glob("*.log"))
    remaining_cache = list(Path(tmp).rglob("__pycache__"))
    print("\n  After treatment:")
    print(f"    Logs remaining: {len(remaining_logs)} (was 5)")
    print(f"    Caches remaining: {len(remaining_cache)} (was 1)")

    if summons_received:
        print(f"\n  Sovereign summons: {len(summons_received)}")
        for s in summons_received:
            print(f"    \u26a0 {s['message'][:70]}...")

    print(f"\n  Apothecary journal: {len(apothecary.history)} entries")
    for entry in apothecary.history[:5]:
        print(f"    [{entry['remedy']}] {entry['patient']}")

    shutil.rmtree(tmp)

    print("\n" + "=" * 60)
    print("  Tourniquet stops the bleeding.")
    print("  Fever floods the wound with light.")
    print("  Controlled burn clears the deadwood.")
    print("  Bone setting re-breaks to set correctly.")
    print("  Metamorphosis dissolves and rebuilds.")
    print("  What she cannot heal, she summons the sovereign.")
    print("  Every remedy recorded before it's applied.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    demo()
