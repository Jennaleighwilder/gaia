"""
Merlin LLM Feed
---------------
Drop this next to real_merlin.py inside gaia/avalon/.

Wires any LLM (Claude, GPT, local model) into Merlin's Feed/cycle() system
so the model becomes one noisy sensor among seven — not the authority.

The architectural move:
    BEFORE: call LLM → trust the answer
    AFTER:  LLM proposal → Feed in Merlin → cycle() correlates against
            live GAIA, TESS, DACCA signals → Round Table votes → Governor signs

The model's output goes through the same convergence and governance stack
as every other signal. Your code is the authority. The LLM is a feed.

Usage:
    from merlin_llm_feed import make_llm_feed, attach_llm_to_merlin

    # Option A: Claude API
    feed = make_llm_feed(
        provider="claude",
        prompt_fn=lambda context: f"Analyze this situation: {context}",
        context_fn=lambda merlin: merlin.get_latest_signals(),
    )
    merlin.add_feed("llm_proposal", feed)

    # Option B: OpenAI
    feed = make_llm_feed(
        provider="openai",
        model="gpt-4o",
        prompt_fn=lambda context: f"Analyze: {context}",
        context_fn=lambda merlin: merlin.get_latest_signals(),
    )

    # Option C: Any callable (local model, mock, custom)
    feed = make_llm_feed(
        provider="callable",
        callable_fn=lambda prompt: my_local_model(prompt),
        prompt_fn=lambda context: f"Analyze: {context}",
        context_fn=lambda merlin: merlin.get_latest_signals(),
    )

    # Then in Merlin's cycle():
    # 1. LLM.poll() → proposal text
    # 2. Merlin.observe("llm_proposal", text, metadata)
    # 3. Merlin.see() → cross-domain correlation includes LLM output
    # 4. Round Table evaluates LLM proposal alongside GAIA, TESS, DACCA
    # 5. Governor signs or defers
"""

import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass, field
from pathlib import Path

# ── Proposal record ───────────────────────────────────────────────────────────

@dataclass
class LLMProposal:
    """One proposal from the LLM feed — the unit Merlin observes."""
    text: str
    model: str
    provider: str
    prompt_used: str
    context_snapshot: Dict = field(default_factory=dict)
    latency_ms: float = 0.0
    token_count: int = 0
    timestamp: str = ""
    proposal_hash: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.proposal_hash:
            self.proposal_hash = hashlib.sha256(
                self.text.encode()
            ).hexdigest()[:16]

    def to_signal_data(self) -> dict:
        """Format for Merlin's observe() call."""
        return {
            "proposal": self.text,
            "model": self.model,
            "provider": self.provider,
            "hash": self.proposal_hash,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp,
        }

    def to_feed_text(self) -> str:
        """The signal text Merlin pattern-matches against."""
        return self.text


# ── LLM client wrappers ───────────────────────────────────────────────────────

def _call_claude(prompt: str, model: str = "claude-sonnet-4-20250514", **kwargs) -> tuple[str, int]:
    """Call Claude API. Returns (response_text, approx_tokens)."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        t0 = time.time()
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        )
        latency = (time.time() - t0) * 1000
        text = msg.content[0].text if msg.content else ""
        tokens = msg.usage.input_tokens + msg.usage.output_tokens if msg.usage else 0
        return text, tokens, latency
    except ImportError:
        raise RuntimeError("anthropic package not installed: pip install anthropic")
    except Exception as e:
        raise RuntimeError(f"Claude API error: {e}")


def _call_openai(prompt: str, model: str = "gpt-4o", **kwargs) -> tuple[str, int, float]:
    """Call OpenAI API. Returns (response_text, tokens, latency_ms)."""
    try:
        from openai import OpenAI
        client = OpenAI()
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            **kwargs,
        )
        latency = (time.time() - t0) * 1000
        text = resp.choices[0].message.content if resp.choices else ""
        tokens = resp.usage.total_tokens if resp.usage else 0
        return text, tokens, latency
    except ImportError:
        raise RuntimeError("openai package not installed: pip install openai")
    except Exception as e:
        raise RuntimeError(f"OpenAI API error: {e}")


def _call_callable(fn: Callable, prompt: str) -> tuple[str, int, float]:
    """Call any callable (local model, mock). Returns (text, 0, latency_ms)."""
    t0 = time.time()
    result = fn(prompt)
    latency = (time.time() - t0) * 1000
    return str(result), 0, latency


# ── Feed factory ──────────────────────────────────────────────────────────────

class LLMFeed:
    """
    A Merlin Feed that polls an LLM for proposals.

    Implements the same interface as real_merlin.Feed so it can be
    added directly to Merlin's feed registry:
        merlin.add_feed("llm_proposal", llm_feed)

    On each poll():
    1. context_fn(merlin) gathers current signal context
    2. prompt_fn(context) builds the prompt
    3. LLM is called
    4. LLMProposal is returned as the feed's "data"
    5. Merlin observes it as a signal in domain "llm_proposal"
    """

    def __init__(
        self,
        provider: str,
        prompt_fn: Callable[[Any], str],
        context_fn: Callable[[Any], Any],
        model: str = "",
        callable_fn: Optional[Callable] = None,
        schedule_seconds: int = 60,
        domain: str = "llm_proposal",
        log_dir: Optional[Path] = None,
        **api_kwargs,
    ):
        self.provider = provider.lower()
        self.prompt_fn = prompt_fn
        self.context_fn = context_fn
        self.model = model or self._default_model()
        self.callable_fn = callable_fn
        self.schedule_seconds = schedule_seconds
        self.domain = domain
        self.log_dir = log_dir
        self.api_kwargs = api_kwargs
        self._history: list = []
        self._last_poll: float = 0.0

        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def _default_model(self) -> str:
        defaults = {
            "claude": "claude-sonnet-4-20250514",
            "openai": "gpt-4o",
            "callable": "custom",
        }
        return defaults.get(self.provider, "unknown")

    def poll(self, merlin_instance: Any = None) -> Optional[LLMProposal]:
        """
        Poll the LLM. Called by Merlin's cycle().
        Returns an LLMProposal or None on error.
        """
        now = time.time()
        if now - self._last_poll < self.schedule_seconds:
            return None  # Not time yet
        self._last_poll = now

        try:
            context = self.context_fn(merlin_instance)
            prompt = self.prompt_fn(context)

            if self.provider == "claude":
                text, tokens, latency = _call_claude(prompt, self.model, **self.api_kwargs)
            elif self.provider == "openai":
                text, tokens, latency = _call_openai(prompt, self.model, **self.api_kwargs)
            elif self.provider == "callable" and self.callable_fn:
                text, tokens, latency = _call_callable(self.callable_fn, prompt)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")

            proposal = LLMProposal(
                text=text,
                model=self.model,
                provider=self.provider,
                prompt_used=prompt[:500],  # truncate for storage
                context_snapshot=context if isinstance(context, dict) else {"raw": str(context)[:500]},
                latency_ms=round(latency, 1),
                token_count=tokens,
            )

            self._history.append(proposal)
            if len(self._history) > 100:
                self._history = self._history[-100:]

            if self.log_dir:
                self._log_proposal(proposal)

            return proposal

        except Exception as e:
            print(f"[LLMFeed/{self.provider}] Poll error: {e}")
            return None

    def _log_proposal(self, proposal: LLMProposal):
        """Log proposal to JSONL for training data capture."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.log_dir / f"llm_proposals_{today}.jsonl"
        record = {
            **proposal.to_signal_data(),
            "prompt_used": proposal.prompt_used,
            "context_snapshot": proposal.context_snapshot,
            "token_count": proposal.token_count,
            "label": "llm_feed_proposal",
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def get_latest(self) -> Optional[LLMProposal]:
        return self._history[-1] if self._history else None

    def get_history(self) -> list:
        return list(self._history)


# ── Merlin integration helper ─────────────────────────────────────────────────

def attach_llm_to_merlin(merlin_instance: Any, feed: "LLMFeed") -> Any:
    """
    Attach the LLM feed to a RealMerlin instance.

    Patches the cycle() method so before each normal cycle,
    the LLM is polled and its proposal is observed as a signal.

    Usage:
        merlin = RealMerlin(config)
        llm_feed = make_llm_feed(provider="claude", ...)
        merlin = attach_llm_to_merlin(merlin, llm_feed)
        # Now merlin.cycle() includes LLM proposals in cross-domain correlation
    """
    original_cycle = merlin_instance.cycle

    def patched_cycle(*args, **kwargs):
        # Poll the LLM first so this signal participates in the same cycle's
        # cross-domain pattern detection.
        proposal = feed.poll(merlin_instance)
        if proposal:
            if hasattr(merlin_instance, "_merlin") and hasattr(merlin_instance._merlin, "observe"):
                merlin_instance._merlin.observe(
                    feed.domain,
                    proposal.to_feed_text(),
                    proposal.to_signal_data(),
                )
            elif hasattr(merlin_instance, "observe"):
                merlin_instance.observe(
                    feed.domain,
                    proposal.to_feed_text(),
                    proposal.to_signal_data(),
                )

        result = original_cycle(*args, **kwargs)

        if proposal and isinstance(result, dict):
            result["llm_proposal"] = proposal.to_signal_data()

        return result

    merlin_instance.cycle = patched_cycle
    return merlin_instance


# ── Convenience factory ───────────────────────────────────────────────────────

def make_llm_feed(
    provider: str,
    prompt_fn: Callable,
    context_fn: Callable,
    model: str = "",
    callable_fn: Optional[Callable] = None,
    schedule_seconds: int = 60,
    log_dir: Optional[Path] = None,
    **kwargs,
) -> LLMFeed:
    """
    Factory function for creating an LLM feed.

    Args:
        provider: "claude", "openai", or "callable"
        prompt_fn: function(context) → prompt string
        context_fn: function(merlin) → context dict/string
        model: model name (optional, uses sensible defaults)
        callable_fn: any callable (for provider="callable")
        schedule_seconds: minimum seconds between polls
        log_dir: if set, log all proposals to JSONL here

    Returns:
        LLMFeed ready to add to Merlin
    """
    return LLMFeed(
        provider=provider,
        prompt_fn=prompt_fn,
        context_fn=context_fn,
        model=model,
        callable_fn=callable_fn,
        schedule_seconds=schedule_seconds,
        log_dir=log_dir,
        **kwargs,
    )


# ── Example usage / test ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Merlin LLM Feed — integration test (mock mode)\n")

    # Mock context and prompt functions
    def mock_context(merlin):
        return {
            "recent_signals": ["GAIA: pressure_drop_detected", "TESS: biotech_M&A_rumor"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def mock_prompt(context):
        signals = context.get("recent_signals", [])
        return (
            f"You are one sensor in a multi-engine governance system. "
            f"Analyze these signals and propose an interpretation. "
            f"Be specific. Note uncertainty. Do not overstate confidence.\n\n"
            f"Current signals: {json.dumps(signals, indent=2)}\n\n"
            f"Proposed interpretation:"
        )

    # Mock callable (replace with real LLM call in production)
    def mock_model(prompt):
        return (
            "Signals suggest elevated atmospheric instability coinciding with "
            "biotech sector M&A activity. Cross-domain convergence probability "
            "moderate (~0.65). Recommend GAIA validation before acting on TESS signal. "
            "DEFER pending additional data points."
        )

    log_dir = Path.home() / "west-os" / "training_data" / "llm_proposals"
    feed = make_llm_feed(
        provider="callable",
        callable_fn=mock_model,
        prompt_fn=mock_prompt,
        context_fn=mock_context,
        schedule_seconds=0,  # immediate poll for testing
        log_dir=log_dir,
    )

    proposal = feed.poll(merlin_instance=None)
    if proposal:
        print("Proposal generated:")
        print(json.dumps(proposal.to_signal_data(), indent=2))
        print(f"\nFull text: {proposal.text}")
        print(f"\nLogged to: {log_dir}")
    else:
        print("No proposal (schedule not elapsed or error)")

    print("\nTo integrate with your real Merlin:")
    print("  from merlin_llm_feed import make_llm_feed, attach_llm_to_merlin")
    print("  feed = make_llm_feed(provider='claude', prompt_fn=..., context_fn=...)")
    print("  merlin = attach_llm_to_merlin(merlin, feed)")
    print("  # Now merlin.cycle() includes LLM proposals in cross-domain correlation")
