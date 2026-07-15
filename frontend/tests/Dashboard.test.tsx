import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommandCenterDashboard } from '@/components/dashboard/CommandCenterDashboard';

import '@testing-library/dom';

describe('CommandCenterDashboard', () => {
  it('renders the Dashboard header without crashing', () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <CommandCenterDashboard />
      </QueryClientProvider>
    );

    expect(screen.getByText(/Command Center/i)).not.toBeNull();
  });
});
