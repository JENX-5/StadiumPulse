import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Separator } from '../src/components/ui/separator';
import { Skeleton } from '../src/components/ui/skeleton';

describe('UI Components', () => {
  describe('Separator', () => {
    it('renders a horizontal separator by default', () => {
      const { container } = render(<Separator data-testid="sep" />);
      const sep = screen.getByTestId('sep');
      expect(sep).toBeTruthy();
      expect(sep.getAttribute('data-orientation')).toBe('horizontal');
    });

    it('renders a vertical separator', () => {
      render(<Separator data-testid="sep-vert" orientation="vertical" />);
      const sep = screen.getByTestId('sep-vert');
      expect(sep.getAttribute('data-orientation')).toBe('vertical');
    });
  });

  describe('Skeleton', () => {
    it('renders a skeleton loader with pulse animation class', () => {
      render(<Skeleton data-testid="skel" className="test-class" />);
      const skeleton = screen.getByTestId('skel');
      expect(skeleton).toBeTruthy();
      expect(skeleton.className).toContain('animate-pulse');
      expect(skeleton.className).toContain('test-class');
    });
  });
});
