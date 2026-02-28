import React from 'react';
import AgentSprite from './AgentSprite';
import './GameRoom.css';

function GameRoom({ agents = [] }) {
  return (
    <div className="game-room">
      {/* Диван */}
      <div className="sofa-unit" style={{ left: 20, top: 80 }}>
        <div className="pixel-sofa sofa">
          <div className="sofa-back"></div>
          <div className="sofa-seat"></div>
          <div className="sofa-arm arm-left"></div>
          <div className="sofa-arm arm-right"></div>
        </div>
        {agents[0] && <AgentSprite agent={agents[0]} />}
      </div>

      {/* Телевизор */}
      <div className="tv-unit" style={{ left: 120, top: 20 }}>
        <div className="tv-stand"></div>
        <div className="pixel-tv tv">
          <div className="tv-screen"></div>
        </div>
      </div>

      {/* Растения */}
      <div className="plants-unit" style={{ left: 160, top: 100 }}>
        <div className="plant pot">
          <div className="plant-leaves">
            <span className="leaf leaf-1">🌿</span>
            <span className="leaf leaf-2">🌱</span>
            <span className="leaf leaf-3">🌿</span>
          </div>
        </div>
      </div>

      <div className="plants-unit" style={{ left: 20, top: 20 }}>
        <div className="plant pot small">
          <div className="plant-leaves">
            <span className="leaf leaf-1">🪴</span>
          </div>
        </div>
      </div>

      {/* Коврик */}
      <div className="rug"></div>
    </div>
  );
}

export default GameRoom;
