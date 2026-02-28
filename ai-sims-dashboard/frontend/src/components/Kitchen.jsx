import React from 'react';
import AgentSprite from './AgentSprite';
import './Kitchen.css';

function Kitchen({ agents = [] }) {
  return (
    <div className="kitchen">
      {/* Холодильник */}
      <div className="fridge-unit" style={{ left: 150, top: 30 }}>
        <div className="pixel-fridge fridge">
          <div className="fridge-door-top"></div>
          <div className="fridge-door-bottom"></div>
          <div className="fridge-handle handle-top"></div>
          <div className="fridge-handle handle-bottom"></div>
        </div>
      </div>

      {/* Кофемашина */}
      <div className="coffee-unit" style={{ left: 120, top: 30 }}>
        <div className="pixel-coffee-machine coffee">
          <div className="coffee-top"></div>
          <div className="coffee-body">
            <div className="coffee-spout"></div>
          </div>
          <div className="coffee-cup"></div>
        </div>
      </div>

      {/* Стол */}
      <div className="table-unit" style={{ left: 30, top: 80 }}>
        <div className="pixel-table table">
          <div className="table-surface"></div>
        </div>
        <div className="table-leg leg-1"></div>
        <div className="table-leg leg-2"></div>
        <div className="table-leg leg-3"></div>
        <div className="table-leg leg-4"></div>
        {agents[0] && <AgentSprite agent={agents[0]} />}
      </div>

      {/* Микроволновка */}
      <div className="microwave-unit" style={{ left: 30, top: 30 }}>
        <div className="microwave">
          <div className="microwave-door">
            <div className="microwave-window"></div>
          </div>
          <div className="microwave-panel">
            <div className="microwave-btn"></div>
            <div className="microwave-btn"></div>
            <div className="microwave-btn"></div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Kitchen;
