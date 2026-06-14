import React, { useEffect, useState } from 'react';

interface SplashScreenProps {
  onDone: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onDone }) => {
  const [phase, setPhase] = useState<'entering' | 'showing' | 'leaving'>('entering');

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('showing'), 50);
    const t2 = setTimeout(() => setPhase('leaving'), 3200);
    const t3 = setTimeout(() => onDone(), 3800);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, [onDone]);

  return (
    <div className={`splash-overlay ${phase}`}>
      {/* Ambient light rays */}
      <div className="splash-rays">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="splash-ray" style={{ '--ray-i': i } as React.CSSProperties} />
        ))}
      </div>

      {/* Floating particles */}
      <div className="splash-particles">
        {[...Array(16)].map((_, i) => (
          <div key={i} className="splash-particle" style={{ '--p-i': i } as React.CSSProperties} />
        ))}
      </div>

      {/* Central content */}
      <div className="splash-center">
        {/* Logo */}
        <div className="splash-logo-wrap">
          <div className="splash-logo-glow" />
          <div className="splash-logo-ring" />
          <img src="/logo-x.svg" width={96} height={96} alt="AutoX" className="splash-logo-img" />
        </div>

        {/* Brand text */}
        <div className="splash-brand">
          <div className="splash-brand-name">
            <span className="splash-brand-autox">AutoX</span>
            <span className="splash-brand-flow"> Flow</span>
            <span className="splash-brand-automate">Automate</span>
          </div>
          <p className="splash-tagline">Visual Workflow Automation · Powered by Temporal</p>
        </div>

        {/* Bottom progress bar */}
        <div className="splash-progress">
          <div className="splash-progress-bar" />
        </div>
      </div>
    </div>
  );
};
