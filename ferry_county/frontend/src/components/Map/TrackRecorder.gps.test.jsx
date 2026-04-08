import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { clearTrackDraft } from "../../lib/trackDrafts.js";
import { TrackRecorder } from "./TrackRecorder.jsx";

describe("TrackRecorder GPS sampling", () => {
  beforeEach(async () => {
    await clearTrackDraft();
    vi.useFakeTimers();
    let n = 0;
    const geo = {
      getCurrentPosition: vi.fn(),
      watchPosition: vi.fn(),
      clearWatch: vi.fn(),
    };
    geo.getCurrentPosition.mockImplementation((success) => {
      const lon = -118.6 + n * 0.001;
      const lat = 48.65 + n * 0.001;
      n += 1;
      success({ coords: { longitude: lon, latitude: lat, accuracy: 5 } });
    });
    Object.defineProperty(navigator, "geolocation", { value: geo, configurable: true });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("records a point every 5 seconds while active", async () => {
    const queueSync = vi.fn();
    render(<TrackRecorder roadId={1} actor="t" queueSync={queueSync} onLineChange={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /start recording/i }));
    expect(navigator.geolocation.getCurrentPosition.mock.calls.length).toBe(1);
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(navigator.geolocation.getCurrentPosition.mock.calls.length).toBe(2);
    await act(async () => {
      vi.advanceTimersByTime(5000);
      await Promise.resolve();
    });
    expect(navigator.geolocation.getCurrentPosition.mock.calls.length).toBe(3);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /stop \(\d+ pts/i }));
    });
    expect(navigator.geolocation.getCurrentPosition.mock.calls.length).toBe(3);
    expect(screen.getByRole("button", { name: /upload track/i })).toBeTruthy();
  });
});
