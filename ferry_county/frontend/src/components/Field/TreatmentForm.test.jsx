import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { TreatmentForm } from "./TreatmentForm.jsx";

describe("TreatmentForm", () => {
  beforeEach(() => {
    vi.stubGlobal("navigator", { ...navigator, onLine: true });
  });

  it("submits and calls onSave with body", async () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(<TreatmentForm roadId={5} disabled={false} actor="tester" onSave={onSave} />);
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    await waitFor(() => expect(onSave).toHaveBeenCalled());
    const [rid, body] = onSave.mock.calls[0];
    expect(rid).toBe(5);
    expect(body).toMatchObject({
      treatment_type: "brush_clear",
      contractor: "Field entry",
    });
  });

  it("shows message when no road selected", async () => {
    const onSave = vi.fn();
    render(<TreatmentForm roadId={null} disabled={false} actor="a" onSave={onSave} />);
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }));
    expect(onSave).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getByText(/select a road/i)).toBeInTheDocument());
  });
});
