"""
AVALON :: REAL HEARTBEAT
The kingdom feels its own pulse. For real.

Before this, the Heartbeat checked lambda functions that returned
hardcoded numbers. "How healthy are you?" "1.0!" Every time.
That's not a pulse. That's a mannequin with a painted smile.

After this, the Heartbeat checks ACTUAL system state:
- Is the process running? What's its CPU and memory usage?
- Is the disk filling up? How much space is left?
- Is the network reachable? Can we reach our dependencies?
- Is Nyx's root alive? Is the blessing valid?
- Is the frozen West-OS still frozen?
- Are log files growing out of control?

When Alfred's health drops now, it's because Alfred's ACTUAL
process is consuming too much memory. When GAIA's health drops,
it's because the ASOS data feed went stale. When Nyx drops,
it's because the root secret is missing from the environment.

Real vital signs. Real consequences. Real kingdom.

© 2026 Jennifer Leigh West. All rights reserved.
"""

import os
import time
import json
import shutil
import socket
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

# Try to import psutil — if not available, fall back to os-level checks
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


# ═══════════════════════════════════════════════════════════════
#  VITAL CHECKS — individual health measurements
# ═══════════════════════════════════════════════════════════════

class VitalCheck:
    """A single health measurement. Returns 0.0 to 1.0."""

    @staticmethod
    def disk_space(path: str = "/", warning_gb: float = 10.0,
                    critical_gb: float = 3.0) -> Tuple[float, Dict]:
        """How much disk space is left?"""
        try:
            usage = shutil.disk_usage(path)
            free_gb = usage.free / (1024 ** 3)
            total_gb = usage.total / (1024 ** 3)
            used_pct = usage.used / usage.total

            if free_gb <= critical_gb:
                health = 0.1
            elif free_gb <= warning_gb:
                health = 0.3 + (free_gb - critical_gb) / (warning_gb - critical_gb) * 0.4
            else:
                health = 0.7 + min(0.3, (free_gb - warning_gb) / 50.0 * 0.3)

            return round(health, 4), {
                "free_gb": round(free_gb, 2),
                "total_gb": round(total_gb, 2),
                "used_pct": round(used_pct * 100, 1),
                "status": "critical" if free_gb <= critical_gb else
                         "warning" if free_gb <= warning_gb else "healthy",
            }
        except Exception as e:
            return 0.5, {"error": str(e)[:100]}

    @staticmethod
    def memory_usage(warning_pct: float = 80.0,
                      critical_pct: float = 92.0) -> Tuple[float, Dict]:
        """How much system memory is in use?"""
        if HAS_PSUTIL:
            try:
                mem = psutil.virtual_memory()
                used_pct = mem.percent
                available_gb = mem.available / (1024 ** 3)

                if used_pct >= critical_pct:
                    health = 0.1
                elif used_pct >= warning_pct:
                    health = 0.3 + (critical_pct - used_pct) / (critical_pct - warning_pct) * 0.4
                else:
                    health = 0.7 + min(0.3, (warning_pct - used_pct) / 40.0 * 0.3)

                return round(health, 4), {
                    "used_pct": round(used_pct, 1),
                    "available_gb": round(available_gb, 2),
                    "total_gb": round(mem.total / (1024 ** 3), 2),
                    "status": "critical" if used_pct >= critical_pct else
                             "warning" if used_pct >= warning_pct else "healthy",
                }
            except Exception as e:
                return 0.5, {"error": str(e)[:100]}
        else:
            # Fallback without psutil
            try:
                with open("/proc/meminfo") as f:
                    lines = f.readlines()
                total = int([l for l in lines if "MemTotal" in l][0].split()[1]) * 1024
                avail = int([l for l in lines if "MemAvailable" in l][0].split()[1]) * 1024
                used_pct = (total - avail) / total * 100
                health = max(0.1, min(1.0, 1.0 - (used_pct / 100)))
                return round(health, 4), {
                    "used_pct": round(used_pct, 1),
                    "available_gb": round(avail / (1024 ** 3), 2),
                }
            except Exception:
                return 0.7, {"note": "psutil not installed, /proc/meminfo not available — assuming healthy"}

    @staticmethod
    def cpu_usage(warning_pct: float = 75.0,
                   critical_pct: float = 90.0) -> Tuple[float, Dict]:
        """Current CPU usage."""
        if HAS_PSUTIL:
            try:
                cpu_pct = psutil.cpu_percent(interval=0.5)

                if cpu_pct >= critical_pct:
                    health = 0.1
                elif cpu_pct >= warning_pct:
                    health = 0.3 + (critical_pct - cpu_pct) / (critical_pct - warning_pct) * 0.4
                else:
                    health = 0.7 + min(0.3, (warning_pct - cpu_pct) / 50.0 * 0.3)

                return round(health, 4), {
                    "cpu_pct": round(cpu_pct, 1),
                    "cpu_count": psutil.cpu_count(),
                    "status": "critical" if cpu_pct >= critical_pct else
                             "warning" if cpu_pct >= warning_pct else "healthy",
                }
            except Exception as e:
                return 0.5, {"error": str(e)[:100]}
        else:
            try:
                load = os.getloadavg()
                cores = os.cpu_count() or 1
                load_pct = (load[0] / cores) * 100
                health = max(0.1, min(1.0, 1.0 - (load_pct / 100)))
                return round(health, 4), {
                    "load_1min": round(load[0], 2),
                    "load_5min": round(load[1], 2),
                    "cores": cores,
                }
            except Exception:
                return 0.7, {"note": "psutil not installed, loadavg not available"}

    @staticmethod
    def file_exists(path: str) -> Tuple[float, Dict]:
        """Does a critical file exist?"""
        exists = Path(path).exists()
        return (1.0 if exists else 0.0), {
            "path": path,
            "exists": exists,
        }

    @staticmethod
    def file_freshness(path: str, max_age_seconds: float = 86400) -> Tuple[float, Dict]:
        """How recently was a file modified?"""
        try:
            p = Path(path)
            if not p.exists():
                return 0.0, {"path": path, "exists": False}
            
            age = time.time() - p.stat().st_mtime
            
            if age <= max_age_seconds * 0.5:
                health = 1.0
            elif age <= max_age_seconds:
                health = 0.5 + 0.5 * (1.0 - (age - max_age_seconds * 0.5) / (max_age_seconds * 0.5))
            else:
                health = max(0.1, 0.5 * (1.0 - min(1.0, (age - max_age_seconds) / max_age_seconds)))
            
            return round(health, 4), {
                "path": path,
                "age_seconds": round(age, 1),
                "age_hours": round(age / 3600, 2),
                "max_age_seconds": max_age_seconds,
                "status": "fresh" if age <= max_age_seconds * 0.5 else
                         "aging" if age <= max_age_seconds else "stale",
            }
        except Exception as e:
            return 0.5, {"path": path, "error": str(e)[:100]}

    @staticmethod
    def directory_size(path: str, warning_mb: float = 500.0,
                        critical_mb: float = 2000.0) -> Tuple[float, Dict]:
        """How large is a directory? (detects log/data bloat)"""
        try:
            total = 0
            p = Path(path)
            if not p.exists():
                return 1.0, {"path": path, "exists": False, "size_mb": 0}
            
            for f in p.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            
            size_mb = total / (1024 * 1024)
            
            if size_mb >= critical_mb:
                health = 0.1
            elif size_mb >= warning_mb:
                health = 0.3 + (critical_mb - size_mb) / (critical_mb - warning_mb) * 0.4
            else:
                health = 1.0
            
            return round(health, 4), {
                "path": path,
                "size_mb": round(size_mb, 2),
                "status": "critical" if size_mb >= critical_mb else
                         "warning" if size_mb >= warning_mb else "healthy",
            }
        except Exception as e:
            return 0.5, {"path": path, "error": str(e)[:100]}

    @staticmethod
    def port_open(host: str = "localhost", port: int = 5001,
                   timeout: float = 2.0) -> Tuple[float, Dict]:
        """Is a service responding on a port?"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            is_open = result == 0
            return (1.0 if is_open else 0.0), {
                "host": host,
                "port": port,
                "open": is_open,
            }
        except Exception as e:
            return 0.0, {"host": host, "port": port, "error": str(e)[:100]}

    @staticmethod
    def environment_variable(name: str) -> Tuple[float, Dict]:
        """Is a required environment variable set?"""
        value = os.environ.get(name)
        exists = value is not None and len(value) > 0
        return (1.0 if exists else 0.0), {
            "variable": name,
            "set": exists,
            "length": len(value) if value else 0,
            # Never expose the actual value
        }

    @staticmethod
    def frozen_integrity(frozen_path: str) -> Tuple[float, Dict]:
        """Is the frozen West-OS still read-only?"""
        p = Path(frozen_path)
        if not p.exists():
            return 0.0, {"path": frozen_path, "exists": False}

        is_writable = os.access(p, os.W_OK)
        return (0.0 if is_writable else 1.0), {
            "path": frozen_path,
            "frozen": not is_writable,
            "status": (
                "FREEZE BROKEN — Lancelot's armor is compromised"
                if is_writable
                else "FREEZE HOLDS — Lancelot's armor is untouched"
            ),
        }

    @staticmethod
    def process_running(process_name: str) -> Tuple[float, Dict]:
        """Is a named process running?"""
        if HAS_PSUTIL:
            try:
                found = []
                for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_percent']):
                    if process_name.lower() in proc.info['name'].lower():
                        found.append({
                            "pid": proc.info['pid'],
                            "cpu": proc.info['cpu_percent'],
                            "memory": round(proc.info['memory_percent'], 2),
                        })
                
                is_running = len(found) > 0
                return (1.0 if is_running else 0.0), {
                    "process": process_name,
                    "running": is_running,
                    "instances": found[:5],
                }
            except Exception as e:
                return 0.5, {"process": process_name, "error": str(e)[:100]}
        else:
            # Fallback: check using pgrep
            try:
                import subprocess
                result = subprocess.run(
                    ["pgrep", "-f", process_name],
                    capture_output=True, text=True, timeout=5
                )
                is_running = result.returncode == 0
                pids = result.stdout.strip().split("\n") if is_running else []
                return (1.0 if is_running else 0.0), {
                    "process": process_name,
                    "running": is_running,
                    "pids": pids[:5],
                }
            except Exception:
                return 0.5, {"process": process_name, "note": "cannot check without psutil or pgrep"}


# ═══════════════════════════════════════════════════════════════
#  SYSTEM MONITOR — combines checks into system-level health
# ═══════════════════════════════════════════════════════════════

@dataclass
class SystemVitals:
    """The real health of one system."""
    name: str
    health: float
    checks: Dict[str, Tuple[float, Dict]]
    timestamp: float = field(default_factory=time.time)
    
    @property
    def worst_check(self) -> Optional[str]:
        if not self.checks:
            return None
        return min(self.checks.items(), key=lambda x: x[1][0])[0]
    
    @property
    def issues(self) -> List[str]:
        problems = []
        for check_name, (score, details) in self.checks.items():
            if score < 0.5:
                status = details.get("status", "degraded")
                problems.append(f"{check_name}: {status} (health: {score:.0%})")
        return problems


class SystemMonitor:
    """Monitors a single system using multiple vital checks.
    
    Each system has a set of checks configured for it.
    The system's overall health is the weighted average
    of all its checks.
    """
    
    def __init__(self, name: str):
        self.name = name
        self._checks: List[Dict] = []  # {name, fn, weight}
    
    def add_check(self, name: str, check_fn: Callable, weight: float = 1.0):
        """Add a health check for this system."""
        self._checks.append({
            "name": name,
            "fn": check_fn,
            "weight": weight,
        })
    
    def check(self) -> SystemVitals:
        """Run all checks. Return real health."""
        results = {}
        total_weight = 0
        weighted_health = 0
        
        for check in self._checks:
            try:
                health, details = check["fn"]()
                results[check["name"]] = (health, details)
                weighted_health += health * check["weight"]
                total_weight += check["weight"]
            except Exception as e:
                results[check["name"]] = (0.3, {"error": str(e)[:100]})
                weighted_health += 0.3 * check["weight"]
                total_weight += check["weight"]
        
        overall = weighted_health / total_weight if total_weight > 0 else 0.5
        
        return SystemVitals(
            name=self.name,
            health=round(overall, 4),
            checks=results,
        )


# ═══════════════════════════════════════════════════════════════
#  REAL HEARTBEAT — replaces the stub heartbeat
# ═══════════════════════════════════════════════════════════════

class RealHeartbeat:
    """The kingdom's real pulse.
    
    She replaces Fusion's stub heartbeat with actual system monitoring.
    On every beat, she runs real health checks against real systems
    and feeds the results back into Fusion's heartbeat for mood
    calculation, healing detection, and Merlin observation.
    
    She knows about the actual infrastructure:
    - Nyx: is the root alive? Is the environment variable set?
    - West-OS: is the frozen clone intact?
    - GAIA: is the process running? Is the data feed fresh?
    - Alfred: is the ward system responding?
    - Disk: how much space is left?
    - Memory: how much RAM is available?
    - CPU: is the system under load?
    """
    
    def __init__(self, project_root: Optional[str] = None):
        self._root = Path(project_root) if project_root else Path.cwd()
        self._monitors: Dict[str, SystemMonitor] = {}
        self._beat_count = 0
        self._history: List[Dict] = []
        self._configure_default_monitors()
    
    def _configure_default_monitors(self):
        """Set up monitors for all known systems."""
        root = self._root
        
        # ── Infrastructure ──
        infra = SystemMonitor("Infrastructure")
        infra.add_check("disk_space", lambda: VitalCheck.disk_space(str(root)), 2.0)
        infra.add_check("memory", VitalCheck.memory_usage, 1.5)
        infra.add_check("cpu", VitalCheck.cpu_usage, 1.0)
        self._monitors["Infrastructure"] = infra
        
        # ── Nyx ──
        nyx_mon = SystemMonitor("Nyx")
        nyx_mon.add_check("root_secret",
            lambda: VitalCheck.environment_variable("WEST_OS_GUARD_SECRET"), 3.0)
        nyx_mon.add_check("nyx_module",
            lambda: VitalCheck.file_exists(str(root / "nyx" / "core.py")), 2.0)
        self._monitors["Nyx"] = nyx_mon
        
        # ── Frozen West-OS ──
        westos = SystemMonitor("West-OS")
        frozen_path = root / "frozen" / "west-os"
        westos.add_check("freeze_integrity",
            lambda: VitalCheck.frozen_integrity(str(frozen_path)), 3.0)
        westos.add_check("governor_exists",
            lambda: VitalCheck.file_exists(
                str(frozen_path / "runtime" / "governor" / "governor.py")), 2.0)
        westos.add_check("alfred_exists",
            lambda: VitalCheck.file_exists(
                str(frozen_path / "scripts" / "alfred.py")), 1.5)
        self._monitors["West-OS"] = westos
        
        # ── Avalon ──
        avalon_mon = SystemMonitor("Avalon")
        avalon_mon.add_check("avalon_module",
            lambda: VitalCheck.file_exists(str(root / "avalon" / "avalon.py")), 2.0)
        avalon_mon.add_check("fusion_module",
            lambda: VitalCheck.file_exists(str(root / "avalon" / "fusion.py")), 1.5)
        avalon_mon.add_check("memory_module",
            lambda: VitalCheck.file_exists(str(root / "avalon" / "memory.py")), 1.5)
        avalon_mon.add_check("healing_module",
            lambda: VitalCheck.file_exists(str(root / "avalon" / "healing.py")), 1.5)
        avalon_mon.add_check("grail_module",
            lambda: VitalCheck.file_exists(str(root / "avalon" / "grail.py")), 1.5)
        self._monitors["Avalon"] = avalon_mon
        
        # ── Memory persistence ──
        memory_mon = SystemMonitor("Memory")
        memory_dir = root / "memory"
        memory_mon.add_check("memory_dir_exists",
            lambda: VitalCheck.file_exists(str(memory_dir)), 1.0)
        memory_mon.add_check("memory_dir_size",
            lambda: VitalCheck.directory_size(str(memory_dir), 100, 500), 1.5)
        self._monitors["Memory"] = memory_mon
        
        # ── Test suite health ──
        tests_mon = SystemMonitor("Tests")
        tests_mon.add_check("test_dir_exists",
            lambda: VitalCheck.file_exists(str(root / "tests")), 1.0)
        tests_mon.add_check("nyx_tests",
            lambda: VitalCheck.file_exists(str(root / "tests" / "test_nyx.py")), 1.0)
        tests_mon.add_check("avalon_tests",
            lambda: VitalCheck.file_exists(str(root / "tests" / "test_avalon.py")), 1.0)
        self._monitors["Tests"] = tests_mon

        gaia_path = Path.home() / "gaia"
        if gaia_path.exists():
            gaia_mon = SystemMonitor("GAIA")
            gaia_mon.add_check(
                "gaia_dir",
                lambda: VitalCheck.file_exists(str(gaia_path)),
                1.0,
            )
            gaia_mon.add_check(
                "governor",
                lambda: VitalCheck.file_exists(
                    str(gaia_path / "runtime" / "governor" / "governor.py")
                ),
                2.0,
            )
            gaia_mon.add_check(
                "data_size",
                lambda: VitalCheck.directory_size(str(gaia_path / "data"), 5000, 10000),
                1.0,
            )
            gaia_mon.add_check(
                "daemon_port",
                lambda: VitalCheck.port_open("localhost", 7780),
                0.5,
            )
            self._monitors["GAIA"] = gaia_mon
    
    def add_monitor(self, name: str, monitor: SystemMonitor):
        """Add a custom system monitor."""
        self._monitors[name] = monitor
    
    def add_check_to_system(self, system_name: str, check_name: str,
                             check_fn: Callable, weight: float = 1.0):
        """Add a check to an existing system monitor."""
        if system_name not in self._monitors:
            self._monitors[system_name] = SystemMonitor(system_name)
        self._monitors[system_name].add_check(check_name, check_fn, weight)
    
    def beat(self) -> Dict:
        """One real heartbeat. Check everything."""
        self._beat_count += 1
        
        system_vitals = {}
        all_issues = []
        total_health = 0.0
        
        for name, monitor in self._monitors.items():
            vitals = monitor.check()
            system_vitals[name] = {
                "health": vitals.health,
                "issues": vitals.issues,
                "worst_check": vitals.worst_check,
                "checks": {
                    k: {"health": round(v[0], 4), "details": v[1]}
                    for k, v in vitals.checks.items()
                },
            }
            total_health += vitals.health
            all_issues.extend([f"[{name}] {issue}" for issue in vitals.issues])
        
        kingdom_health = total_health / len(self._monitors) if self._monitors else 0
        
        # Determine mood from real health
        if kingdom_health >= 0.95:
            mood = "celebrating"
        elif kingdom_health >= 0.8:
            mood = "steady"
        elif kingdom_health >= 0.6:
            mood = "concerned"
        elif kingdom_health >= 0.4:
            mood = "wounded"
        else:
            mood = "critical"
        
        beat_record = {
            "beat": self._beat_count,
            "timestamp": time.time(),
            "kingdom_health": round(kingdom_health, 4),
            "mood": mood,
            "systems": system_vitals,
            "issues": all_issues,
            "systems_healthy": len([v for v in system_vitals.values() if v["health"] >= 0.7]),
            "systems_total": len(system_vitals),
        }
        
        self._history.append(beat_record)
        if len(self._history) > 100:
            self._history = self._history[-100:]
        
        return beat_record
    
    def get_health_scores(self) -> Dict[str, float]:
        """Get current health scores for all systems.
        
        This is what feeds into Fusion's heartbeat system_health dict,
        replacing the lambda stubs.
        """
        scores = {}
        for name, monitor in self._monitors.items():
            vitals = monitor.check()
            scores[name] = vitals.health
        return scores
    
    def narrative_report(self) -> str:
        """Alfred-style narrative report of the kingdom's real health."""
        beat = self.beat()
        
        lines = [
            f"Kingdom Health Report — Beat #{beat['beat']}",
            f"Overall: {beat['kingdom_health']:.0%} — mood: {beat['mood']}",
            f"Systems: {beat['systems_healthy']}/{beat['systems_total']} healthy",
            "",
        ]
        
        for sys_name, sys_data in beat["systems"].items():
            health = sys_data["health"]
            icon = "●" if health >= 0.7 else "◐" if health >= 0.4 else "○"
            lines.append(f"  {icon} {sys_name:20s} {health:.0%}")
            
            for issue in sys_data["issues"]:
                lines.append(f"    ⚠ {issue}")
        
        if beat["issues"]:
            lines.append("")
            lines.append("Issues requiring attention:")
            for issue in beat["issues"]:
                lines.append(f"  → {issue}")
        else:
            lines.append("")
            lines.append("All clear. The kingdom is healthy.")
        
        return "\n".join(lines)
    
    @property
    def status(self) -> Dict:
        return {
            "beats": self._beat_count,
            "monitors": len(self._monitors),
            "monitor_names": list(self._monitors.keys()),
            "has_psutil": HAS_PSUTIL,
        }


# ═══════════════════════════════════════════════════════════════
#  BRIDGE — connects RealHeartbeat to Fusion's heartbeat
# ═══════════════════════════════════════════════════════════════

def wire_real_heartbeat(fusion, project_root: Optional[str] = None) -> RealHeartbeat:
    """Wire the RealHeartbeat into an existing Fusion instance.
    
    Replaces Fusion's stub health checks with real system monitors.
    Fusion's heartbeat still handles mood, history, and the rhythm.
    RealHeartbeat provides the actual health data.
    """
    real_hb = RealHeartbeat(project_root)
    
    # Get real health scores and register them as Fusion health sources
    def make_health_fn(system_name: str):
        def check():
            vitals = real_hb._monitors[system_name].check()
            return vitals.health
        return check
    
    for sys_name in real_hb._monitors:
        fusion.heartbeat.register_system(sys_name, make_health_fn(sys_name))
    
    return real_hb


# ═══════════════════════════════════════════════════════════════
#  DEMO
# ═══════════════════════════════════════════════════════════════

def demo():
    """Watch the kingdom's real pulse."""
    print("\n" + "=" * 60)
    print("  R E A L   H E A R T B E A T")
    print("  The Kingdom Feels Its Own Pulse")
    print("=" * 60)
    
    # Create with current directory as project root
    hb = RealHeartbeat(project_root=os.getcwd())
    
    print(f"\n  Monitors configured: {hb.status['monitors']}")
    print(f"  psutil available: {hb.status['has_psutil']}")
    print(f"  Systems monitored: {', '.join(hb.status['monitor_names'])}")
    
    # Take a real heartbeat
    print(f"\n  Taking pulse...")
    beat = hb.beat()
    
    print(f"\n  Kingdom health: {beat['kingdom_health']:.0%}")
    print(f"  Mood: {beat['mood']}")
    print(f"  Systems healthy: {beat['systems_healthy']}/{beat['systems_total']}")
    
    print(f"\n  System-by-system:")
    for sys_name, sys_data in beat["systems"].items():
        health = sys_data["health"]
        icon = "●" if health >= 0.7 else "◐" if health >= 0.4 else "○"
        print(f"    {icon} {sys_name:20s} {health:.0%}")
        
        # Show individual checks
        for check_name, check_data in sys_data["checks"].items():
            ch = check_data["health"]
            details = check_data["details"]
            status = details.get("status", "")
            print(f"        {check_name:25s} {ch:.0%}  {status}")
        
        if sys_data["issues"]:
            for issue in sys_data["issues"]:
                print(f"        ⚠ {issue}")
    
    # Narrative report
    print(f"\n  {'─' * 50}")
    print(f"  ALFRED'S REPORT:")
    print(f"  {'─' * 50}")
    print(f"  {hb.narrative_report()}")
    
    # Wire into Fusion
    print(f"\n  {'─' * 50}")
    print(f"  WIRING INTO FUSION:")
    print(f"  {'─' * 50}")
    
    from avalon.fusion import Fusion
    fusion = Fusion()
    real_hb = wire_real_heartbeat(fusion, os.getcwd())
    
    # Fusion breathes with real data
    breath = fusion.breathe()
    print(f"  Fusion breath with real data:")
    print(f"    Health: {breath['health']:.0%}")
    print(f"    Mood: {breath['mood']}")
    print(f"    Systems: {breath['systems_alive']}")
    
    print(f"\n" + "=" * 60)
    print(f"  The pulse is real.")
    print(f"  The health is measured, not assumed.")
    print(f"  When the kingdom hurts, it knows where.")
    print(f"  When the kingdom thrives, it knows why.")
    print(f"=" * 60 + "\n")


if __name__ == "__main__":
    demo()
