import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AgentOrb, { STAGE_TO_ORB_STATE, normalizeOrbSize } from '../components/common/AgentOrb';
import { ThemeProvider } from '../components/ThemeContext';

describe('AgentOrb Component', () => {
  it('normalizes arbitrary sizes to thinking-orbs presets', () => {
    expect(normalizeOrbSize(20)).toBe(20);
    expect(normalizeOrbSize(16)).toBe(20);
    expect(normalizeOrbSize(32)).toBe(32);
    expect(normalizeOrbSize(48)).toBe(32);
    expect(normalizeOrbSize(64)).toBe(64);
    expect(normalizeOrbSize(128)).toBe(64);
  });

  it('renders with testid and default properties', () => {
    render(
      <ThemeProvider>
        <AgentOrb state="solving" size={64} />
      </ThemeProvider>
    );
    const orbContainer = screen.getByTestId('agent-orb');
    expect(orbContainer).toBeInTheDocument();
  });

  it('correctly maps pipeline stages to orb states', () => {
    expect(STAGE_TO_ORB_STATE['ingesting']).toBe('shaping');
    expect(STAGE_TO_ORB_STATE['similarity']).toBe('solving');
    expect(STAGE_TO_ORB_STATE['web_dragnet']).toBe('searching');
    expect(STAGE_TO_ORB_STATE['report_generation']).toBe('composing');
    expect(STAGE_TO_ORB_STATE['complete']).toBe('breathing');
  });

  it('renders with inline 20px size for table badges', () => {
    render(
      <ThemeProvider>
        <AgentOrb stage="ingesting" size={20} />
      </ThemeProvider>
    );
    const orbContainer = screen.getByTestId('agent-orb');
    expect(orbContainer).toBeInTheDocument();
  });
});
