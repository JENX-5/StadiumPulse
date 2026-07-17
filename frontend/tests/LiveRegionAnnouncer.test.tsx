import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { LiveRegionAnnouncer } from "@/components/layout/LiveRegionAnnouncer";
import { useAppStore } from "@/store/useAppStore";

describe("LiveRegionAnnouncer", () => {
  beforeEach(() => {
    useAppStore.setState({ timelineEvents: [] });
  });

  it("renders an empty, always-present aria-live region when there are no events", () => {
    render(<LiveRegionAnnouncer />);

    const region = screen.getByRole("status");
    expect(region.getAttribute("aria-live")).toBe("polite");
    expect(region.textContent).toBe("");
  });

  it("announces a new incident event", () => {
    useAppStore.setState({
      timelineEvents: [
        { id: "evt-1", type: "incident.created", timestamp: "2026-07-17T00:00:00Z", payload: {} },
      ],
    });

    render(<LiveRegionAnnouncer />);

    expect(screen.getByRole("status").textContent).toBe("New incident reported.");
  });

  it("does not announce routine simulation ticks", () => {
    useAppStore.setState({
      timelineEvents: [
        { id: "evt-2", type: "simulation.tick", timestamp: "2026-07-17T00:00:00Z", payload: {} },
      ],
    });

    render(<LiveRegionAnnouncer />);

    expect(screen.getByRole("status").textContent).toBe("");
  });
});
