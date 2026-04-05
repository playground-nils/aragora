'use client';

import { useTheme } from '@/context/ThemeContext';
import { Header } from './Header';
import { HeroSection } from './HeroSection';
import { LiveDemoSection } from './LiveDemoSection';
import { HowItWorksSection } from './HowItWorksSection';
import { ProblemSection } from './ProblemSection';
import { PricingSection } from './PricingSection';
import { Footer } from './Footer';

export interface LandingPageProps {
  /** Backend API base URL. HeroSection resolves this internally via useBackend
   *  when omitted, so this is only needed for non-standard configurations. */
  apiBase?: string;
  /** WebSocket URL override. Like apiBase, HeroSection resolves this via useBackend. */
  wsUrl?: string;
  /** Callback fired when the user clicks "Log in" in the Header. When provided,
   *  this replaces the default Link-based navigation to /login. Useful for the
   *  inline landing page in HomePage where return-URL storage is needed before
   *  the redirect. */
  onEnterDashboard?: () => void;
}

export function LandingPage({ onEnterDashboard }: LandingPageProps = {}) {
  const { theme } = useTheme();

  return (
    <div
      className="min-h-screen"
      style={{
        backgroundColor: 'var(--bg)',
        color: 'var(--text)',
        fontFamily: 'var(--font-landing)',
      }}
      data-landing-theme={theme}
    >
      <Header onLoginClick={onEnterDashboard} />
      <HeroSection />
      <LiveDemoSection />
      <HowItWorksSection />
      <ProblemSection />
      <PricingSection />
      <Footer />
    </div>
  );
}
