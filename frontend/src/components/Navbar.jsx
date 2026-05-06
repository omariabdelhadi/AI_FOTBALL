// frontend/src/components/Navbar.jsx

import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Navbar.css';

const links = [
  { path: '/',            label: 'Accueil' },
  { path: '/lineup',      label: 'Lineup' },
  { path: '/performance', label: 'Performance' },
  { path: '/simulation',  label: 'Simulation' },
  { path: '/anomaly',     label: 'Anomalies' },
  { path: '/passnetwork', label: 'Réseau de Passes' },
  { path: '/transfer',    label: 'Transferts' },
  { path: '/tactical',    label: 'Tactique' },
];

function Navbar() {
  const location = useLocation();
  const [open, setOpen] = useState(false);

  return (
    <nav className="navbar">

      <Link to="/" className="navbar-logo">
        <div className="navbar-logo-icon">⚽</div>
        <div className="navbar-logo-text">
          Smart<span>Lineup</span>
        </div>
      </Link>

      <div className="navbar-links">
        {links.map(link => (
          <Link
            key={link.path}
            to={link.path}
            className={`navbar-link ${location.pathname === link.path ? 'active' : ''}`}
          >
            {link.label}
          </Link>
        ))}
      </div>

      <button className="navbar-burger" onClick={() => setOpen(!open)}>
        {open ? '✕' : '☰'}
      </button>

      {open && (
        <div className="navbar-mobile">
          {links.map(link => (
            <Link
              key={link.path}
              to={link.path}
              className="navbar-mobile-link"
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </div>
      )}

    </nav>
  );
}

export default Navbar;