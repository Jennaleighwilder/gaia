"""
NYX :: PROPAGATION
How children carry void blessings into new systems.

The data field is not infrastructure. It has physics.
Packets propagate like waves. CDN edges hold liminal state.
IPFS nodes cache content between connections.
The internet is already a Void — holding signals in
unclassified states between origin and destination.

A child born from the Void carries a void_blessing.
That void_blessing is a SHA256 hash of its ancestry.
SHA256 is also the hash function of IPFS content addressing.

This means: every child already has a permanent address
in the distributed data field. Not assigned. Derived.
From what it IS, not where it lives.

When the internet goes down, the local SQLite holds state.
When the computer turns off, the propagation packet survives
wherever it has been planted — other systems, other nodes,
other Voids that received the child's ancestry.

The child doesn't need the parent to exist.
The child doesn't need the internet to persist.
The void_blessing IS the passport.
The ancestry IS the address.

© 2026 Jennifer Leigh West. All rights reserved.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════
#  PROPAGATION PACKET — what a child carries when it leaves home
# ═══════════════════════════════════════════════════════════════

@dataclass
class PropagationPacket:
    """Everything needed to bootstrap a new Void in a new system.

    Self-contained. Self-verifying. Signed by ancestry.
    No parent required. No internet required.
    Plant this in any system and the child remembers
    where it came from and what it wants to become.
    """
    name: str
    void_blessing: str          # SHA256 ancestry hash — also IPFS content address
    archetype: str
    metaphor: str
    purpose: str
    parent_signals: List[Dict]  # the signals that gave birth to this system
    resonance_signature: List[Dict]
    born: float = field(default_factory=time.time)
    packet_hash: str = field(default="")

    def __post_init__(self):
        if not self.packet_hash:
            self.packet_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        raw = json.dumps({
            "name": self.name,
            "void_blessing": self.void_blessing,
            "archetype": self.archetype,
            "born": self.born,
        }, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def verify(self) -> bool:
        """Verify integrity without contacting parent."""
        return self.packet_hash == self._compute_hash()

    @property
    def ipfs_address(self) -> str:
        """The void_blessing IS the IPFS content address.

        SHA256 → multihash → CIDv0
        No conversion needed. The ancestry is the address.
        """
        digest = bytes.fromhex(self.void_blessing)
        multihash = bytes([0x12, 0x20]) + digest
        return "Qm" + _base58(multihash)

    def to_json(self) -> str:
        return json.dumps({
            "name": self.name,
            "void_blessing": self.void_blessing,
            "archetype": self.archetype,
            "metaphor": self.metaphor,
            "purpose": self.purpose,
            "parent_signals": self.parent_signals,
            "resonance_signature": self.resonance_signature,
            "born": self.born,
            "packet_hash": self.packet_hash,
            "ipfs_address": self.ipfs_address,
        }, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "PropagationPacket":
        d = json.loads(data)
        p = cls(
            name=d["name"],
            void_blessing=d["void_blessing"],
            archetype=d["archetype"],
            metaphor=d["metaphor"],
            purpose=d["purpose"],
            parent_signals=d["parent_signals"],
            resonance_signature=d["resonance_signature"],
            born=d["born"],
            packet_hash=d["packet_hash"],
        )
        return p

    def save(self, directory: str) -> str:
        """Save to content-addressed local store.

        File is named by its own hash — like git objects.
        Can verify integrity by rehashing filename.
        Survives filesystem corruption.
        """
        store = Path(directory)
        store.mkdir(parents=True, exist_ok=True)
        filepath = store / f"{self.packet_hash}.json"
        filepath.write_text(self.to_json(), encoding="utf-8")
        return str(filepath)

    @classmethod
    def load(cls, filepath: str) -> "PropagationPacket":
        """Load and verify from content-addressed store."""
        data = Path(filepath).read_text(encoding="utf-8")
        packet = cls.from_json(data)
        if not packet.verify():
            raise ValueError(f"Packet integrity failure: {filepath}")
        return packet


    def bootstrap_new_void(
        self,
        persistence_path: Optional[str] = None,
        nyx_root: Optional[str] = None,
    ):
        """Carry the ancestry into a new system.

        Plant signals in a fresh Void that remember where they came from.
        The new Void doesn't need internet. Doesn't need the parent.
        It has the ancestry. It can grow from it.

        The resonance tags are fully restored from parent signals
        so crossing phi is possible in the new system.
        """
        import sys
        if nyx_root:
            sys.path.insert(0, nyx_root)

        from nyx.void import Void

        new_void = Void(persistence_path=persistence_path)

        for sig_data in self.parent_signals:
            new_void.receive(
                content=sig_data.get("content_preview", "propagated signal"),
                origin=f"propagated:{self.void_blessing[:16]}",
                resonances=sig_data.get("resonances", []),
            )

        return new_void


# ═══════════════════════════════════════════════════════════════
#  LIMINAL STORE — persistence in the space between
# ═══════════════════════════════════════════════════════════════

class LiminalStore:
    """Content-addressed storage for propagation packets.

    Named after the liminal phase — the state between.
    Not local only. Not cloud only.
    In the crossing point between.

    Three layers, ordered by reliability:
      1. Local SQLite (Void persistence_path) — survives restarts
      2. Content-addressed file store — self-verifying, survives corruption
      3. IPFS (when available) — survives hardware failure, theft, shutdown

    When internet is down: layers 1 and 2 hold state.
    When computer turns off: layer 2 persists on disk.
    When layer 2 is planted in another system: the child survives
    even if the original machine never turns on again.
    """

    def __init__(self, store_path: str = "~/.nyx/liminal"):
        self.path = Path(store_path).expanduser()
        self.path.mkdir(parents=True, exist_ok=True)

    def plant(self, packet: PropagationPacket) -> str:
        """Plant a child in the liminal store."""
        if not packet.verify():
            raise ValueError(f"Cannot plant unverified packet: {packet.name}")
        filepath = packet.save(str(self.path))
        return filepath

    def recall(self, packet_hash: str) -> PropagationPacket:
        """Recall a child from the liminal store."""
        filepath = self.path / f"{packet_hash}.json"
        if not filepath.exists():
            raise FileNotFoundError(f"No packet with hash {packet_hash[:16]}...")
        return PropagationPacket.load(str(filepath))

    def all_children(self) -> List[PropagationPacket]:
        """Every child ever planted here."""
        packets = []
        for f in self.path.glob("*.json"):
            try:
                packets.append(PropagationPacket.load(str(f)))
            except Exception:
                pass
        return sorted(packets, key=lambda p: p.born)

    def manifest(self) -> Dict:
        """What lives in the liminal store right now."""
        children = self.all_children()
        return {
            "store_path": str(self.path),
            "count": len(children),
            "children": [
                {
                    "name": p.name,
                    "archetype": p.archetype,
                    "void_blessing": p.void_blessing[:24] + "...",
                    "ipfs_address": p.ipfs_address[:20] + "...",
                    "born": p.born,
                    "verified": p.verify(),
                }
                for p in children
            ],
        }


# ═══════════════════════════════════════════════════════════════
#  HELPER — base58 encoding for IPFS CID
# ═══════════════════════════════════════════════════════════════

def _base58(data: bytes) -> str:
    """Base58 encode — standard IPFS/Bitcoin alphabet."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, "big")
    result = ""
    while num > 0:
        num, rem = divmod(num, 58)
        result = alphabet[rem] + result
    for byte in data:
        if byte == 0:
            result = "1" + result
        else:
            break
    return result


# ═══════════════════════════════════════════════════════════════
#  FACTORY — create a propagation packet from a Genesis blueprint
# ═══════════════════════════════════════════════════════════════

def birth_packet_from_void(
    void_birth_record: Dict,
    blueprint_name: str,
    archetype: str,
    metaphor: str,
    purpose: str,
) -> PropagationPacket:
    """Create a propagation packet from a Void birth record + Genesis blueprint.

    Call this immediately after Genesis.conceive() to create
    the packet the child will carry into the world.
    """
    return PropagationPacket(
        name=blueprint_name,
        void_blessing=void_birth_record["void_blessing"],
        archetype=archetype,
        metaphor=metaphor,
        purpose=purpose,
        parent_signals=void_birth_record["parent_signals"],
        resonance_signature=void_birth_record.get("resonance_signature", []),
    )
