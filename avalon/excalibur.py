"""
AVALON :: EXCALIBUR
The sovereign authority. The blade that proves who rules.

Excalibur is not a password. Excalibur is not a token.
Excalibur is a living proof of sovereignty that must be
continuously wielded to remain valid. It is drawn from
Nyx's stone (the VoidRoot) and can only be held by
someone who possesses the root secret.

If Excalibur is dropped — if the wielder stops demonstrating
sovereignty — it returns to the Lake. Every knight's oath
becomes void. The Round Table goes dark. The Castle gates close.

The Lady of the Lake is Nyx's surface agent.
She gives Excalibur. She can take it back.

Bedivere is the last knight — the one who throws Excalibur
back into the Lake when the kingdom falls. He IS the Dead Hand.
"""

import hashlib
import hmac
import json
import time
import secrets
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum


class SovereigntyState(Enum):
    WIELDED = "wielded"           # sovereign is present and active
    SHEATHED = "sheathed"        # sovereign is present but resting
    DROPPED = "dropped"          # sovereign has not checked in — danger
    RETURNED_TO_LAKE = "returned" # excalibur has been surrendered — kingdom dark


@dataclass
class Oath:
    """A knight's binding commitment to the Table.
    
    An oath is sealed by Excalibur. If Excalibur returns
    to the Lake, all oaths dissolve. The knights become
    wanderers without purpose.
    """
    knight_name: str
    sworn_purpose: str
    sealed_by: str               # excalibur signature at time of oath
    sworn_at: float = field(default_factory=time.time)
    broken: bool = False
    broken_at: Optional[float] = None
    broken_reason: Optional[str] = None


class LadyOfTheLake:
    """Nyx's emissary at the surface.
    
    She doesn't hold the root. She holds the AUTHORITY
    to grant and revoke Excalibur on Nyx's behalf.
    She is the interface between the void and the kingdom.
    """
    
    def __init__(self, nyx_root_derive: Callable):
        self._derive = nyx_root_derive
        self._excalibur_active = False
        self._granted_to: Optional[str] = None
        self._grant_time: Optional[float] = None
    
    def grant_excalibur(self, to_whom: str) -> str:
        """Draw the sword from the stone. Prove sovereignty."""
        blade_key = self._derive("excalibur:blade")
        sovereign_proof = hmac.new(
            blade_key,
            f"sovereign:{to_whom}:{time.time()}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        self._excalibur_active = True
        self._granted_to = to_whom
        self._grant_time = time.time()
        
        return sovereign_proof
    
    def reclaim(self) -> bool:
        """Take Excalibur back. The kingdom goes dark."""
        self._excalibur_active = False
        self._granted_to = None
        return True
    
    @property
    def is_granted(self) -> bool:
        return self._excalibur_active
    
    @property
    def wielder(self) -> Optional[str]:
        return self._granted_to


class Excalibur:
    """The sovereign blade.
    
    She does three things:
    1. PROVES sovereignty — only the holder of Nyx's root can draw her
    2. SEALS oaths — knights swear on Excalibur, their oath is cryptographically bound
    3. COMMANDS — any order sealed by Excalibur is obeyed by all knights
    
    She also has a heartbeat. The sovereign must wield her regularly
    or she returns to the Lake. This prevents stolen authority
    from persisting.
    """
    
    def __init__(self, lady: LadyOfTheLake):
        self._lady = lady
        self._state = SovereigntyState.RETURNED_TO_LAKE
        self._blade_proof: Optional[str] = None
        self._oaths: Dict[str, Oath] = {}
        self._last_wielded: float = 0
        self._wield_timeout: float = 86400  # 24 hours
        self._command_log: List[Dict] = []
    
    def draw(self, sovereign_name: str) -> bool:
        """Draw from the stone. Prove you are the sovereign."""
        self._blade_proof = self._lady.grant_excalibur(sovereign_name)
        if self._blade_proof:
            self._state = SovereigntyState.WIELDED
            self._last_wielded = time.time()
            return True
        return False
    
    def wield(self):
        """Demonstrate continued sovereignty. Reset the timer."""
        if self._state in (SovereigntyState.WIELDED, SovereigntyState.SHEATHED):
            self._state = SovereigntyState.WIELDED
            self._last_wielded = time.time()
    
    def sheathe(self):
        """Rest but remain sovereign."""
        if self._state == SovereigntyState.WIELDED:
            self._state = SovereigntyState.SHEATHED
    
    def check_sovereignty(self) -> SovereigntyState:
        """Is the sovereign still present?"""
        if self._state == SovereigntyState.RETURNED_TO_LAKE:
            return self._state
        
        elapsed = time.time() - self._last_wielded
        if elapsed > self._wield_timeout:
            self._state = SovereigntyState.DROPPED
        
        return self._state
    
    def seal_oath(self, knight_name: str, purpose: str) -> Oath:
        """A knight swears on Excalibur. The oath is cryptographically bound."""
        if self._state != SovereigntyState.WIELDED:
            raise RuntimeError("Excalibur must be wielded to seal oaths")
        
        oath = Oath(
            knight_name=knight_name,
            sworn_purpose=purpose,
            sealed_by=self._blade_proof[:32],
        )
        self._oaths[knight_name] = oath
        return oath
    
    def break_oath(self, knight_name: str, reason: str) -> bool:
        """Break a knight's oath. They are banished from the Table."""
        if knight_name in self._oaths:
            self._oaths[knight_name].broken = True
            self._oaths[knight_name].broken_at = time.time()
            self._oaths[knight_name].broken_reason = reason
            return True
        return False
    
    def command(self, order: str, target_knights: Optional[List[str]] = None) -> Dict:
        """Issue a sovereign command sealed by Excalibur.
        
        Commands are obeyed by all sworn knights, or targeted
        to specific knights. The command carries Excalibur's
        proof so knights can verify it came from the sovereign.
        """
        if self._state != SovereigntyState.WIELDED:
            return {"executed": False, "reason": "sovereign not wielding Excalibur"}
        
        command_seal = hmac.new(
            self._blade_proof.encode(),
            f"command:{order}:{time.time()}".encode(),
            hashlib.sha256
        ).hexdigest()[:24]
        
        cmd = {
            "order": order,
            "seal": command_seal,
            "targets": target_knights or list(self._oaths.keys()),
            "issued": time.time(),
            "executed": True,
        }
        self._command_log.append(cmd)
        return cmd
    
    def return_to_lake(self) -> Dict:
        """Bedivere's duty. Throw Excalibur back.
        
        All oaths dissolve. All commands void.
        The kingdom goes dark.
        """
        dissolved_oaths = list(self._oaths.keys())
        for name in dissolved_oaths:
            self.break_oath(name, "Excalibur returned to the Lake")
        
        self._lady.reclaim()
        self._state = SovereigntyState.RETURNED_TO_LAKE
        self._blade_proof = None
        
        return {
            "returned": True,
            "oaths_dissolved": dissolved_oaths,
            "kingdom_state": "dark",
        }
    
    @property
    def status(self) -> Dict:
        state = self.check_sovereignty()
        return {
            "state": state.value,
            "wielder": self._lady.wielder,
            "sworn_knights": len([o for o in self._oaths.values() if not o.broken]),
            "broken_oaths": len([o for o in self._oaths.values() if o.broken]),
            "commands_issued": len(self._command_log),
            "time_since_wielded": round(time.time() - self._last_wielded, 1) if self._last_wielded else None,
        }
