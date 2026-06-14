import React from 'react';

interface LoaderProps {
  label?: string;
}

export const Loader: React.FC<LoaderProps> = ({ label = 'Processing…' }) => (
  <div className="autox-loader-overlay">
    <div className="autox-loader-content">
      <div className="autox-loader-logo-wrap">
        <div className="autox-loader-ring" />
        <img
          src="/logo-x.svg"
          width={36}
          height={36}
          alt="AutoX"
          className="autox-loader-logo"
          style={{ borderRadius: '8px' }}
        />
      </div>
      <span className="autox-loader-label">{label}</span>
    </div>
  </div>
);
