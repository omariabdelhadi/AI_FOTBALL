// frontend/src/App.js

import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Lineup from './pages/Lineup';
import Performance from './pages/Performance';
import Simulation from './pages/Simulation';
import Anomaly from './pages/Anomaly';
import Transfer from './pages/Transfer';
import Tactical from './pages/Tactical';
import Comparison from './pages/Comparison';
import PassNetwork from './pages/PassNetwork';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="main-content">
          <Routes>
            <Route path="/"            element={<Home />} />
            <Route path="/lineup"      element={<Lineup />} />
            <Route path="/performance" element={<Performance />} />
            <Route path="/simulation"  element={<Simulation />} />
            <Route path="/anomaly"     element={<Anomaly />} />
            <Route path="/transfer"    element={<Transfer />} />
            <Route path="/comparison" element={<Comparison />} />
            <Route path="/tactical"    element={<Tactical />} />
            <Route path="/passnetwork"    element={<PassNetwork />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;