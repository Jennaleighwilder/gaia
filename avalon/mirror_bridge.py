"""
AVALON :: MIRROR BRIDGE
Read-only adapter to Mirror OS / East OS.

Mirror is the fourth sacred system. She does not live inside the
kingdom repo and the kingdom does not rewrite her orders. This
bridge only reads her structure, probes her HTTP surface when she
is awake, and reads the preserved West-Mirror contract from the
frozen West-OS clone.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional


class MirrorBridge:
    """Read-only bridge to Mirror OS / East OS."""

    def __init__(
        self,
        mirror_path: Optional[Path] = None,
        mirror_port: Optional[int] = None,
        timeout: float = 2.0,
        frozen_west_os_path: Optional[Path] = None,
    ):
        self.mirror_path = (
            Path(mirror_path)
            if mirror_path
            else Path("/Users/jenniferwest/Documents/New project/mirror_os_software")
        )
        self.timeout = timeout
        self._port_override = mirror_port
        if frozen_west_os_path:
            self.frozen_west_os_path = Path(frozen_west_os_path)
        else:
            project_root = Path(__file__).resolve().parent.parent
            frozen_candidate = project_root / "frozen" / "west-os"
            self.frozen_west_os_path = frozen_candidate if frozen_candidate.exists() else None
        self._structure_cache: Optional[Dict[str, Any]] = None
        self._discovered_port: Optional[int] = None

    @property
    def is_available(self) -> bool:
        return self.mirror_path.exists()

    @property
    def port(self) -> int:
        if self._port_override is not None:
            return self._port_override
        if self._discovered_port is not None:
            return self._discovered_port
        self._discovered_port = self._discover_port_from_server()
        return self._discovered_port

    @property
    def is_running(self) -> bool:
        return bool(self._http_health().get("available"))

    @property
    def status(self) -> Dict[str, Any]:
        health = self.health()
        return {
            "available": health.get("available", False),
            "running": health.get("running", False),
            "health": health.get("health", 0.0),
            "path": str(self.mirror_path),
            "port": health.get("port", self.port),
            "mode": health.get("mode", "structure"),
        }

    def read_structure(self) -> Dict[str, Any]:
        """Read Mirror OS's filesystem structure without modifying it."""
        if not self.is_available:
            return {
                "available": False,
                "reason": f"Mirror OS not found at {self.mirror_path}",
            }

        structure: Dict[str, Any] = {
            "available": True,
            "path": str(self.mirror_path),
            "codename": "Mirror",
            "external_name": "East Runtime Governor",
        }

        readme = self.mirror_path / "README.md"
        if readme.exists():
            try:
                content = readme.read_text(errors="ignore")
                lines = content.splitlines()
                non_heading = [
                    line.strip()
                    for line in lines
                    if line.strip() and not line.lstrip().startswith("#")
                ]
                structure["readme"] = {
                    "exists": True,
                    "lines": len(lines),
                    "summary": " ".join(non_heading[:3])[:320],
                }
            except OSError:
                structure["readme"] = {"exists": True, "readable": False}

        engine = self.mirror_path / "lib" / "mirror-engine.js"
        if engine.exists():
            try:
                content = engine.read_text(errors="ignore")
                lines = content.splitlines()
                structure["engine"] = {
                    "exists": True,
                    "lines": len(lines),
                    "exports": sum(
                        1
                        for line in lines
                        if "module.exports" in line or line.strip().startswith("export ")
                    ),
                    "functions": sum(
                        1
                        for line in lines
                        if line.strip().startswith("function ")
                        or "=>" in line
                        or line.strip().startswith("async function ")
                    ),
                }
            except OSError:
                structure["engine"] = {"exists": True, "readable": False}
        else:
            structure["engine"] = {"exists": False}

        server = self.mirror_path / "server.js"
        if server.exists():
            try:
                content = server.read_text(errors="ignore")
                lines = content.splitlines()
                port_hints = [
                    line.strip()
                    for line in lines
                    if "PORT" in line and any(ch.isdigit() for ch in line)
                ]
                structure["server"] = {
                    "exists": True,
                    "lines": len(lines),
                    "port": self._discover_port_from_text(content),
                    "port_hints": port_hints[:3],
                }
            except OSError:
                structure["server"] = {"exists": True, "readable": False}
        else:
            structure["server"] = {"exists": False}

        package_file = self.mirror_path / "package.json"
        if package_file.exists():
            try:
                package = json.loads(package_file.read_text())
                structure["package"] = {
                    "exists": True,
                    "name": package.get("name"),
                    "version": package.get("version"),
                    "description": package.get("description", "")[:240],
                    "main": package.get("main"),
                    "scripts": sorted(list((package.get("scripts") or {}).keys())),
                    "script_count": len(package.get("scripts") or {}),
                    "dependencies": len(package.get("dependencies") or {}),
                    "dev_dependencies": len(package.get("devDependencies") or {}),
                }
            except (OSError, json.JSONDecodeError):
                structure["package"] = {"exists": True, "readable": False}

        js_files = [
            path for path in self.mirror_path.rglob("*.js") if "node_modules" not in str(path)
        ]
        structure["js_files"] = len(js_files)
        structure["total_js_lines"] = sum(self._line_count(path) for path in js_files)

        script_dir = self.mirror_path / "scripts"
        if script_dir.exists():
            structure["script_files"] = len(list(script_dir.glob("*.js")))

        data_dir = self.mirror_path / "data"
        if data_dir.exists():
            structure["data_files"] = len([path for path in data_dir.rglob("*") if path.is_file()])

        self._structure_cache = structure
        return structure

    def read_integration_surfaces(self) -> Dict[str, Any]:
        """Read the preserved West-Mirror contract from frozen West-OS."""
        if not self.frozen_west_os_path or not self.frozen_west_os_path.exists():
            return {
                "available": False,
                "reason": "frozen West-OS path not configured",
                "files": {},
            }

        surfaces: Dict[str, Any] = {"available": True, "files": {}}
        targets = {
            "mirror_shadow_bridge": self.frozen_west_os_path
            / "runtime"
            / "governor"
            / "mirror_shadow_bridge.py",
            "mirror_protocol_service": self._find_integration_file("mirror_protocol_service.py"),
        }

        for name, path in targets.items():
            if not path or not path.exists():
                surfaces["files"][name] = {"exists": False}
                continue
            try:
                content = path.read_text(errors="ignore")
                lines = content.splitlines()
                functions = [
                    line.strip()
                    for line in lines
                    if line.strip().startswith("def ") or line.strip().startswith("async def ")
                ]
                classes = [line.strip() for line in lines if line.strip().startswith("class ")]
                surfaces["files"][name] = {
                    "exists": True,
                    "path": str(path.relative_to(self.frozen_west_os_path)),
                    "lines": len(lines),
                    "functions": len(functions),
                    "classes": len(classes),
                    "function_names": [
                        fn.split("(")[0].replace("async def ", "").replace("def ", "").strip()
                        for fn in functions[:10]
                    ],
                }
            except OSError:
                surfaces["files"][name] = {"exists": True, "readable": False}
        return surfaces

    def health(self) -> Dict[str, Any]:
        """Mirror OS health from structure plus HTTP availability."""
        result: Dict[str, Any] = {
            "system": "Mirror OS / East OS",
            "codename": "Mirror",
            "path": str(self.mirror_path),
            "port": self.port,
        }

        if not self.is_available:
            result.update(
                {
                    "available": False,
                    "directory": "missing",
                    "engine": "missing",
                    "running": False,
                    "health": 0.0,
                }
            )
            return result

        structure = self._structure_cache or self.read_structure()
        result["available"] = True
        result["directory"] = "present"
        result["engine"] = "present" if structure.get("engine", {}).get("exists") else "missing"
        result["server_file"] = (
            "present" if structure.get("server", {}).get("exists") else "missing"
        )

        http = self._http_health()
        if http.get("available"):
            result.update(
                {
                    "running": True,
                    "mode": "http",
                    "health": 0.98,
                    "probe": http.get("details"),
                    "port": http.get("port", self.port),
                }
            )
            return result

        result.update(
            {
                "running": False,
                "mode": "structure",
                "health": 0.8 if structure.get("engine", {}).get("exists") else 0.3,
                "reason": http.get("error", "Mirror OS sleeping"),
            }
        )
        return result

    def reflection(self) -> Dict[str, Any]:
        """Ask Mirror OS what she sees, without writing to her."""
        if not self.is_available:
            return {
                "available": False,
                "mirror_running": False,
                "reflection": "Mirror OS is not present. The kingdom cannot see its own reflection.",
            }

        health = self._http_health()
        if health.get("available"):
            posture = self._http_json("/api/deployment-posture")
            bootstrap = self._http_json("/api/bootstrap")
            proof = self._http_json("/api/proof-bundle")

            reflection: Dict[str, Any] = {
                "available": True,
                "mirror_running": True,
                "mode": "http",
                "port": health.get("port", self.port),
                "health": health.get("details", {}),
                "posture": posture.get("data") if posture.get("ok") else {},
                "bootstrap": bootstrap.get("data") if bootstrap.get("ok") else {},
                "proof_bundle": proof.get("data") if proof.get("ok") else {},
            }

            bootstrap_data = reflection["bootstrap"] or {}
            posture_data = reflection["posture"] or {}
            proof_data = reflection["proof_bundle"] or {}

            reflection["reflection"] = (
                "Mirror OS is awake. "
                f"Deployment posture: {posture_data.get('deploymentMode', posture_data.get('deployment_mode', 'unknown'))}. "
                f"Sessions: {bootstrap_data.get('sessionCount', 0)}. "
                f"Bridge cases: {bootstrap_data.get('bridgeCount', 0)}. "
                f"Kernel events: {bootstrap_data.get('kernelEventCount', 0)}. "
                f"Proof bundle keys: {len(proof_data) if isinstance(proof_data, dict) else 0}."
            )
            return reflection

        structure = self._structure_cache or self.read_structure()
        return {
            "available": True,
            "mirror_running": False,
            "mode": "structure",
            "structure": {
                "engine_lines": structure.get("engine", {}).get("lines", 0),
                "js_files": structure.get("js_files", 0),
                "total_js_lines": structure.get("total_js_lines", 0),
                "scripts": structure.get("package", {}).get("script_count", 0),
            },
            "reflection": (
                "Mirror OS is present but sleeping. "
                f"Her engine holds {structure.get('engine', {}).get('lines', '?')} lines, "
                f"{structure.get('js_files', '?')} JavaScript files, and "
                f"{structure.get('package', {}).get('script_count', '?')} named scripts. "
                "When she wakes, she will read the kingdom from within."
            ),
        }

    def _find_integration_file(self, filename: str) -> Optional[Path]:
        if not self.frozen_west_os_path or not self.frozen_west_os_path.exists():
            return None
        matches = list(self.frozen_west_os_path.rglob(filename))
        return matches[0] if matches else None

    def _line_count(self, path: Path) -> int:
        try:
            return len(path.read_text(errors="ignore").splitlines())
        except OSError:
            return 0

    def _discover_port_from_server(self) -> int:
        server = self.mirror_path / "server.js"
        if not server.exists():
            return 3000
        try:
            return self._discover_port_from_text(server.read_text(errors="ignore"))
        except OSError:
            return 3000

    def _discover_port_from_text(self, content: str) -> int:
        patterns = [
            r"PORT\s*=\s*Number\([^)]*\|\|\s*(\d+)\)",
            r"PORT\s*=\s*(\d+)",
            r"port\s*[:=]\s*(\d{4,5})",
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))
        return 3000

    def _candidate_ports(self) -> List[int]:
        candidates = [self.port]
        if self.port != 3030:
            candidates.append(3030)
        if self.port != 3000:
            candidates.append(3000)
        seen = set()
        ordered = []
        for candidate in candidates:
            if candidate not in seen:
                ordered.append(candidate)
                seen.add(candidate)
        return ordered

    def _http_json(self, endpoint: str) -> Dict[str, Any]:
        for port in self._candidate_ports():
            url = f"http://127.0.0.1:{port}{endpoint}"
            try:
                request = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    raw = response.read().decode()
                data = json.loads(raw) if raw else {}
                return {"ok": True, "data": data, "port": port, "url": url}
            except (
                urllib.error.URLError,
                urllib.error.HTTPError,
                TimeoutError,
                json.JSONDecodeError,
            ) as exc:
                last_error = str(exc)[:200]
        return {"ok": False, "error": last_error}

    def _http_health(self) -> Dict[str, Any]:
        result = self._http_json("/api/health")
        if not result.get("ok"):
            return {"available": False, "error": result.get("error", "health probe failed")}
        return {
            "available": True,
            "port": result.get("port", self.port),
            "details": result.get("data", {}),
        }


def wire_mirror_bridge(
    avalon,
    mirror_path: Optional[Path] = None,
    mirror_port: Optional[int] = None,
) -> MirrorBridge:
    """Wire the Mirror bridge into Avalon using the frozen contract when present."""
    project_root = Path(__file__).resolve().parent.parent
    frozen_candidate = project_root / "frozen" / "west-os"
    frozen = frozen_candidate if frozen_candidate.exists() else None
    return MirrorBridge(
        mirror_path=mirror_path,
        mirror_port=mirror_port,
        frozen_west_os_path=frozen,
    )


def demo():
    """Show what the kingdom can read from Mirror OS."""
    print("\n" + "=" * 60)
    print("  T H E   M I R R O R   B R I D G E")
    print("  The Kingdom's Introspective Layer")
    print("=" * 60)

    bridge = MirrorBridge()
    print(f"\n  Mirror OS path: {bridge.mirror_path}")
    print(f"  Available: {bridge.is_available}")

    if bridge.is_available:
        structure = bridge.read_structure()
        print("\n  STRUCTURE:")
        print(f"    Engine: {structure.get('engine', {}).get('lines', '?')} lines")
        print(f"    JS files: {structure.get('js_files', '?')}")
        print(f"    Total JS lines: {structure.get('total_js_lines', '?')}")
        print(f"    Port: {structure.get('server', {}).get('port', bridge.port)}")

        print("\n  INTEGRATION SURFACES:")
        surfaces = bridge.read_integration_surfaces()
        for name, data in surfaces.get("files", {}).items():
            if data.get("exists"):
                print(
                    f"    {name}: {data.get('lines', '?')} lines, "
                    f"{data.get('functions', '?')} functions"
                )
            else:
                print(f"    {name}: not found")

        health = bridge.health()
        print("\n  HEALTH:")
        print(f"    Running: {health.get('running', False)}")
        print(f"    Health: {health.get('health', 0):.0%}")

        reflection = bridge.reflection()
        print("\n  REFLECTION:")
        print(f"    {reflection.get('reflection', 'No reflection available')}")
    else:
        print("\n  Mirror OS not found. The kingdom cannot see inward yet.")

    print("\n" + "=" * 60)
    print("  West-OS looks outward at threats.")
    print("  GAIA looks outward at weather.")
    print("  Nyx holds identity.")
    print("  Mirror OS looks inward.")
    print("  Four sacred systems. Four read-only bridges.")
    print("  The kingdom sees in all directions.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    demo()
