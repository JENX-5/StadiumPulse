import { describe, it, expect, beforeEach } from 'vitest';
import { useAppStore } from '../src/store/useAppStore';

describe('useAppStore', () => {
  beforeEach(() => {
    // Reset state before each test
    useAppStore.setState({ 
      venueId: 'venue_123', 
      activeView: 'map', 
      timelineEvents: [],
      liveState: null
    });
  });

  it('should initialize with default state', () => {
    const state = useAppStore.getState();
    expect(state.venueId).toBe('venue_123');
    expect(state.activeView).toBe('map');
  });

  it('should update live state correctly', () => {
    const store = useAppStore.getState();
    const payload = { 
      venue_id: 'venue_123', 
      risk_score: 85, 
      active_incidents: 2, 
      timestamp: '2026-07-14' 
    };
    
    store.updateLiveState(payload);
    
    const newState = useAppStore.getState();
    expect(newState.liveState?.risk_score).toBe(85);
    expect(newState.liveState?.active_incidents).toBe(2);
  });
});
