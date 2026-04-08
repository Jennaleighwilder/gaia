import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RoadSelector } from "./RoadSelector.jsx";

describe("RoadSelector", () => {
  it("lists roads and calls onChange with numeric id", () => {
    const onChange = vi.fn();
    render(
      <RoadSelector
        roads={[
          { id: 1, road_name: "Alpha", road_number: "100", source_feature_id: "fc_abc123" },
          { id: 2, road_name: "Beta", road_number: null, source_feature_id: "fc_def456" },
        ]}
        value={null}
        onChange={onChange}
      />
    );
    const select = screen.getByRole("combobox", { name: /road/i });
    fireEvent.change(select, { target: { value: "2" } });
    expect(onChange).toHaveBeenCalledWith(2);
  });
});
