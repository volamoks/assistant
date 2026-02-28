import React from 'react';
import AgentSprite from './AgentSprite';
import './BossOffice.css';

function BossOffice({ agents = [] }) {
  const mainAgent = agents.find(a => a.isMain);

  return (
    <div className="boss-office">
      {/* Большой стол */}
      <div className="boss-desk-unit" style={{ left: 80, top: 60 }}>
        <div className="boss-desk">
          <div className="desk-top">
            <div className="desk-lamp"></div>
            <div className="desk-computer">
              <div className="boss-monitor">
                <div className="boss-screen"></div>
              </div>
            </div>
            <div className="desk-items">
              <div className="desk-phone"></div>
              <div className="desk-papers"></div>
            </div>
          </div>
          <div className="desk-body"></div>
        </div>
        <div className="desk-leg leg-1"></div>
        <div className="desk-leg leg-2"></div>
        {mainAgent && <AgentSprite agent={mainAgent} />}
      </div>

      {/* Кресло руководителя */}
      <div className="boss-chair-unit" style={{ left: 120, top: 110 }}>
        <div className="boss-chair">
          <div className="chair-back-large"></div>
          <div className="chair-seat-large"></div>
          <div className="chair-arm arm-1"></div>
          <div className="chair-arm arm-2"></div>
        </div>
        <div className="chair-pillar"></div>
        <div className="chair-base">
          <div className="wheel w1"></div>
          <div className="wheel w2"></div>
          <div className="wheel w3"></div>
        </div>
      </div>

      {/* Сейф */}
      <div className="safe-unit" style={{ left: 180, top: 30 }}>
        <div className="pixel-safe safe">
          <div className="safe-door">
            <div className="safe-dial"></div>
            <div className="safe-handle"></div>
          </div>
        </div>
      </div>

      {/* Флаг/символ */}
      <div className="decor-unit" style={{ left: 20, top: 30 }}>
        <div className="flag-pole">
          <div className="flag"></div>
        </div>
      </div>

      {/* Растение */}
      <div className="plant-boss" style={{ left: 180, top: 130 }}>
        <div className="plant pot">
          <div className="plant-leaves">
            <span className="leaf">🌴</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default BossOffice;
