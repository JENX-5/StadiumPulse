import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useAuthStore } from '../src/store/useAuthStore';
import { UserRole } from '../src/lib/auth-constants';

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset state before each test
    useAuthStore.setState({ 
      token: null,
      user: null,
      isAuthenticated: false
    });
    
    // Mock document.cookie
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: ''
    });
  });

  it('should initialize with default state', () => {
    const state = useAuthStore.getState();
    expect(state.token).toBeNull();
    expect(state.user).toBeNull();
    expect(state.isAuthenticated).toBe(false);
  });

  it('should update state and set cookie on login', () => {
    const store = useAuthStore.getState();
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'dispatcher' as UserRole,
      venue_id: 'venue_456'
    };
    
    store.login('fake-jwt-token', mockUser);
    
    const newState = useAuthStore.getState();
    expect(newState.isAuthenticated).toBe(true);
    expect(newState.token).toBe('fake-jwt-token');
    expect(newState.user).toEqual(mockUser);
    expect(document.cookie).toContain('fake-jwt-token');
  });

  it('should clear state and cookie on logout', () => {
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      full_name: 'Test User',
      role: 'dispatcher' as UserRole,
      venue_id: 'venue_456'
    };
    
    useAuthStore.getState().login('fake-jwt-token', mockUser);
    
    useAuthStore.getState().logout();
    
    const newState = useAuthStore.getState();
    expect(newState.isAuthenticated).toBe(false);
    expect(newState.token).toBeNull();
    expect(newState.user).toBeNull();
    expect(document.cookie).toContain('max-age=0');
  });
});
