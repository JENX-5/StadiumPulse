import { config } from "@/lib/config";
import { useAppStore } from "@/store/useAppStore";

let ws: WebSocket | null = null;
let reconnectTimer: NodeJS.Timeout | null = null;
let pingTimer: NodeJS.Timeout | null = null;
let shouldReconnect = true;
let queryClientInstance: any = null;

export function connectWebSocket(queryClient?: any) {
  if (queryClient) {
    queryClientInstance = queryClient;
  }

  if (typeof window === "undefined") return; // Only run on client

  if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
    return;
  }

  shouldReconnect = true;
  console.log("Connecting to WebSocket:", config.wsUrl);
  ws = new WebSocket(config.wsUrl);

  ws.onopen = () => {
    console.log("WebSocket connected.");
    if (reconnectTimer) clearTimeout(reconnectTimer);
    
    // Setup ping interval to keep connection alive
    pingTimer = setInterval(() => {
      if (ws?.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);
  };

  ws.onmessage = (event) => {
    if (event.data === "pong") return;
    
    try {
      const parsedEvent = JSON.parse(event.data);
      console.log("Received WS Event:", parsedEvent);
      
      const store = useAppStore.getState();
      
      // Update global timeline
      store.addTimelineEvent({
        id: parsedEvent.event_id || Math.random().toString(),
        type: parsedEvent.event_type,
        timestamp: parsedEvent.occurred_at || new Date().toISOString(),
        payload: parsedEvent.payload,
      });

      // Handle specific operational state updates
      if (parsedEvent.event_type === "simulation.tick" || parsedEvent.event_type === "state.updated") {
        store.updateLiveState(parsedEvent.payload);
        // Feed the risk trajectory sparkline
        if (parsedEvent.payload?.global_crowd_density != null) {
          store.pushRiskScore(parsedEvent.payload.global_crowd_density);
        }
      }

      // Invalidate queries so that UI fetches fresh data without polling
      if (queryClientInstance) {
        queryClientInstance.invalidateQueries({ queryKey: ["incidents"] });
        queryClientInstance.invalidateQueries({ queryKey: ["resources"] });
        queryClientInstance.invalidateQueries({ queryKey: ["metrics"] });
        queryClientInstance.invalidateQueries({ queryKey: ["simulation-status"] });
      }
      
    } catch (e) {
      console.error("Failed to parse WebSocket message:", e);
    }
  };

  ws.onclose = () => {
    console.warn("WebSocket disconnected. Reconnecting in 5s...");
    if (pingTimer) clearInterval(pingTimer);
    pingTimer = null;
    ws = null;
    if (shouldReconnect) {
      reconnectTimer = setTimeout(connectWebSocket, 5000);
    }
  };

  ws.onerror = (err) => {
    console.warn("WebSocket error:", err);
    ws?.close();
  };
}

export function disconnectWebSocket() {
  shouldReconnect = false;
  if (reconnectTimer) clearTimeout(reconnectTimer);
  reconnectTimer = null;
  if (pingTimer) clearInterval(pingTimer);
  pingTimer = null;
  if (ws) {
    ws.close();
    ws = null;
  }
}
