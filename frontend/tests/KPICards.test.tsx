import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { KPICards } from '../src/components/metrics/KPICards';
import { useAppStore } from '../src/store/useAppStore';

// Mock recharts because ResponsiveContainer does not work well in jsdom
vi.mock('recharts', async () => {
  const OriginalRecharts = await vi.importActual('recharts');
  return {
    ...OriginalRecharts,
    ResponsiveContainer: ({ children }: any) => <div>{children}</div>,
    LineChart: ({ children }: any) => <div>{children}</div>,
    Line: () => <div />,
    Tooltip: () => <div />,
  };
});

describe('KPICards', () => {
  it('renders metric cards correctly', () => {
    useAppStore.setState({ venueId: 'venue_123', liveState: { venue_id: 'venue_123', active_incidents: 0, global_crowd_density: 0.75, global_noise_level: 0, available_resources: 0 } });
    
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <KPICards />
      </QueryClientProvider>
    );

    // It should render Active Incidents, Crowd Density, Resource Readiness, Avg Response
    expect(screen.getByText(/Active Incidents/i)).toBeTruthy();
    expect(screen.getByText(/Crowd Density/i)).toBeTruthy();
    expect(screen.getByText(/Resource Readiness/i)).toBeTruthy();
    expect(screen.getByText(/Avg Response/i)).toBeTruthy();
    
    // Check if the density value is rendered (75.0%)
    expect(screen.getByText('75.0%')).toBeTruthy();
  });
});
