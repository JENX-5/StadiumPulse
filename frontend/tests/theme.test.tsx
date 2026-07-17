import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ThemeToggle } from '../src/components/layout/ThemeToggle';
import { ThemeProvider } from '../src/components/theme-provider';
import React from 'react';

// Mock next-themes
const mockSetTheme = vi.fn();
let mockResolvedTheme = 'light';

vi.mock('next-themes', () => ({
  useTheme: () => ({
    resolvedTheme: mockResolvedTheme,
    setTheme: mockSetTheme,
  }),
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <div data-testid="theme-provider">{children}</div>,
}));

describe('Theme Components', () => {
  describe('ThemeProvider', () => {
    it('renders children within NextThemesProvider', () => {
      render(
        <ThemeProvider>
          <div>Child Content</div>
        </ThemeProvider>
      );
      expect(screen.getByTestId('theme-provider')).toBeTruthy();
      expect(screen.getByText('Child Content')).toBeTruthy();
    });
  });

  describe('ThemeToggle', () => {
    it('renders correctly and toggles theme when clicked', () => {
      mockResolvedTheme = 'light';
      render(<ThemeToggle />);
      
      const button = screen.getByRole('button', { name: /toggle theme/i });
      expect(button).toBeTruthy();
      
      // Should show moon icon in light mode
      expect(button.getAttribute('title')).toBe('Switch to dark mode');
      
      fireEvent.click(button);
      expect(mockSetTheme).toHaveBeenCalledWith('dark');
    });

    it('shows sun icon when in dark mode', () => {
      mockResolvedTheme = 'dark';
      render(<ThemeToggle />);
      
      const button = screen.getByRole('button', { name: /toggle theme/i });
      expect(button.getAttribute('title')).toBe('Switch to light mode');
      
      fireEvent.click(button);
      expect(mockSetTheme).toHaveBeenCalledWith('light');
    });
  });
});
