import React, { useEffect, useState } from 'react';

const RAYS = ['ra','rb','rc','rd','re','rf','rg','rh'];
const PARTICLES = ['pa','pb','pc','pd','pe','pf','pg','ph','pi','pj','pk','pl','pm','pn','po','pp'];

interface SplashScreenProps {
  onDone: () => void;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onDone }) => {
  const [phase, setPhase] = useState<'showing' | 'leaving'>('showing');

  useEffect(() => {
    const t1 = setTimeout(() => setPhase('leaving'), 3200);
    const t2 = setTimeout(() => onDone(), 3800);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [onDone]);

  return (
    <div className={`splash-overlay ${phase}`}>
      {/* Ambient light rays */}
      <div className="splash-rays">
        {RAYS.map((id, i) => (
          <div key={id} className="splash-ray" style={{ '--ray-i': i } as React.CSSProperties} />
        ))}
      </div>

      {/* Floating particles */}
      <div className="splash-particles">
        {PARTICLES.map((id, i) => (
          <div key={id} className="splash-particle" style={{ '--p-i': i } as React.CSSProperties} />
        ))}
      </div>

      {/* Central content */}
      <div className="splash-center">
        {/* Logo */}
        <div className="splash-logo-wrap">
          <div className="splash-logo-glow" />
          <div className="splash-logo-ring" />
          <img src="/logo-x.svg" width={76} height={76} alt="AutoX" className="splash-logo-img" />
        </div>

        {/* Brand text */}
        <div className="splash-brand">
          <div className="splash-brand-name">
            <span className="splash-brand-flow">Flow</span>
            <span className="splash-brand-automate">Automate</span>
          </div>
          <p className="splash-tagline">Visual Workflow Automation Platform</p>
        </div>

        {/* Bottom progress bar */}
        <div className="splash-progress">
          <div className="splash-progress-bar" />
        </div>
      </div>
    </div>
  );
};
