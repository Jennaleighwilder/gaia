import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SyncStatus } from "./SyncStatus.jsx";

describe("SyncStatus", () => {
  it("shows online state and calls onFlush", () => {
    const onFlush = vi.fn();
    render(
      <SyncStatus pending={2} flushing={false} lastError={null} onFlush={onFlush} online />
    );
    expect(screen.getByText(/online/i)).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /sync now/i }));
    expect(onFlush).toHaveBeenCalled();
  });

  it("disables sync when offline", () => {
    render(
      <SyncStatus pending={1} flushing={false} lastError={null} onFlush={vi.fn()} online={false} />
    );
    expect(screen.getByText(/offline/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sync now/i })).toBeDisabled();
  });
});
