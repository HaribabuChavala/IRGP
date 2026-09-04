import { setAuthReturnTarget, getAuthReturnTarget, clearAuthReturnTarget } from '../keycloak';

describe('keycloak return target helpers', () => {
  beforeEach(() => {
    sessionStorage.clear();
    // ensure origin exists in jsdom
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost/'),
      writable: true,
    });
  });

  test('stores simple path', () => {
    setAuthReturnTarget('/reports');
    expect(sessionStorage.getItem('report_platform_return_to')).toBe('/reports');
    expect(getAuthReturnTarget()).toBe('/reports');
  });

  test('stores full URL with querystring as path', () => {
    setAuthReturnTarget('http://localhost/some/page?x=1');
    expect(sessionStorage.getItem('report_platform_return_to')).toBe('/some/page?x=1');
    expect(getAuthReturnTarget()).toBe('/some/page?x=1');
  });

  test('does not store login or callback paths (simple and full URL)', () => {
    setAuthReturnTarget('/login');
    expect(sessionStorage.getItem('report_platform_return_to')).toBe('/dashboard');
    setAuthReturnTarget('http://localhost/auth/callback?token=1');
    expect(sessionStorage.getItem('report_platform_return_to')).toBe('/dashboard');
  });

  test('getAuthReturnTarget falls back to supplied default', () => {
    expect(getAuthReturnTarget('/foo')).toBe('/foo');
  });

  test('clearAuthReturnTarget removes stored value', () => {
    setAuthReturnTarget('/x');
    expect(sessionStorage.getItem('report_platform_return_to')).toBe('/x');
    clearAuthReturnTarget();
    expect(sessionStorage.getItem('report_platform_return_to')).toBeNull();
  });
});
