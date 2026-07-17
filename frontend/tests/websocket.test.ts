import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const addTimelineEvent = vi.fn();
const updateLiveState = vi.fn();
const pushRiskScore = vi.fn();

vi.mock("@/store/useAppStore", () => ({
  useAppStore: {
    getState: () => ({ addTimelineEvent, updateLiveState, pushRiskScore }),
  },
}));

const authState: { token: string | null } = { token: "test-jwt-token" };
vi.mock("@/store/useAuthStore", () => ({
  useAuthStore: {
    getState: () => authState,
  },
}));

vi.mock("@/lib/config", () => ({
  config: { apiUrl: "http://test-host/api/v1", wsUrl: "ws://test-host/ws" },
}));

class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;
  static instances: MockWebSocket[] = [];

  readyState = MockWebSocket.CONNECTING;
  sent: string[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((err: unknown) => void) | null = null;

  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  }

  /** Test helper: simulate the browser completing the handshake. */
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.();
  }
}

function lastSocket(): MockWebSocket {
  const socket = MockWebSocket.instances.at(-1);
  if (!socket) throw new Error("expected a MockWebSocket instance to have been created");
  return socket;
}

describe("websocket service", () => {
  let connectWebSocket: typeof import("@/services/websocket").connectWebSocket;
  let disconnectWebSocket: typeof import("@/services/websocket").disconnectWebSocket;

  beforeEach(async () => {
    vi.useFakeTimers();
    MockWebSocket.instances = [];
    // @ts-expect-error -- test double, not a full WebSocket implementation
    global.WebSocket = MockWebSocket;

    vi.resetModules();
    const mod = await import("@/services/websocket");
    connectWebSocket = mod.connectWebSocket;
    disconnectWebSocket = mod.disconnectWebSocket;

    addTimelineEvent.mockClear();
    updateLiveState.mockClear();
    pushRiskScore.mockClear();
  });

  afterEach(() => {
    disconnectWebSocket();
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("opens a connection to config.wsUrl with the auth token attached", () => {
    connectWebSocket();
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(lastSocket().url).toBe("ws://test-host/ws?token=test-jwt-token");
  });

  it("does not attempt to connect when there is no auth token", () => {
    authState.token = null;
    try {
      connectWebSocket();
      expect(MockWebSocket.instances).toHaveLength(0);
    } finally {
      authState.token = "test-jwt-token";
    }
  });

  it("does not open a second connection while one is connecting or open", () => {
    connectWebSocket();
    connectWebSocket();
    expect(MockWebSocket.instances).toHaveLength(1);
  });

  it("sends a ping every 30s once the connection is open", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    vi.advanceTimersByTime(30000);
    expect(socket.sent).toEqual(["ping"]);

    vi.advanceTimersByTime(30000);
    expect(socket.sent).toEqual(["ping", "ping"]);
  });

  it("ignores 'pong' messages", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onmessage?.({ data: "pong" });

    expect(addTimelineEvent).not.toHaveBeenCalled();
  });

  it("records every parsed event on the timeline", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onmessage?.({
      data: JSON.stringify({
        event_id: "evt-1",
        event_type: "incident.created",
        occurred_at: "2026-07-17T00:00:00Z",
        payload: { incident_id: "inc-1" },
      }),
    });

    expect(addTimelineEvent).toHaveBeenCalledWith({
      id: "evt-1",
      type: "incident.created",
      timestamp: "2026-07-17T00:00:00Z",
      payload: { incident_id: "inc-1" },
    });
  });

  it("updates live state and pushes the risk sparkline on a simulation.tick event", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onmessage?.({
      data: JSON.stringify({
        event_type: "simulation.tick",
        payload: { global_crowd_density: 0.72, global_noise_level: 80 },
      }),
    });

    expect(updateLiveState).toHaveBeenCalledWith({ global_crowd_density: 0.72, global_noise_level: 80 });
    expect(pushRiskScore).toHaveBeenCalledWith(0.72);
  });

  it("does not push a risk score when the tick payload has no crowd density", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onmessage?.({
      data: JSON.stringify({ event_type: "state.updated", payload: { active_incidents: 3 } }),
    });

    expect(updateLiveState).toHaveBeenCalledWith({ active_incidents: 3 });
    expect(pushRiskScore).not.toHaveBeenCalled();
  });

  it("does not throw on malformed JSON and does not update the store", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => socket.onmessage?.({ data: "not-json" })).not.toThrow();
    expect(addTimelineEvent).not.toHaveBeenCalled();

    consoleError.mockRestore();
  });

  it("invalidates the relevant query keys when a query client is supplied", () => {
    const invalidateQueries = vi.fn();
    connectWebSocket({ invalidateQueries });
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onmessage?.({
      data: JSON.stringify({ event_type: "state.updated", payload: {} }),
    });

    const invalidatedKeys = invalidateQueries.mock.calls.map((call) => call[0].queryKey[0]);
    expect(invalidatedKeys).toEqual(
      expect.arrayContaining(["incidents", "resources", "metrics", "simulation-status"])
    );
  });

  it("schedules a reconnect 5s after the socket closes", () => {
    connectWebSocket();
    const firstSocket = lastSocket();
    firstSocket.close();

    expect(MockWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(5000);
    expect(MockWebSocket.instances).toHaveLength(2);
  });

  it("closes the socket on error", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    socket.onerror?.(new Event("error"));

    expect(socket.readyState).toBe(MockWebSocket.CLOSED);
  });

  it("disconnectWebSocket prevents any pending reconnect and stops the ping timer", () => {
    connectWebSocket();
    const socket = lastSocket();
    socket.simulateOpen();

    disconnectWebSocket();
    expect(socket.readyState).toBe(MockWebSocket.CLOSED);

    vi.advanceTimersByTime(35000);
    // No reconnect and no further pings sent past the disconnect.
    expect(MockWebSocket.instances).toHaveLength(1);
    expect(socket.sent).toEqual([]);
  });
});
