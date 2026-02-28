import React from 'react';
import AgentSprite from './AgentSprite';
import './WorkZone.css';

function WorkZone({ agents = [] }) {
  const desks = [
    { id: 1, x: 20, y: 30 },
    { id: 2, x: 120, y: 30 },
    { id: 3, x: 20, y: 100 },
    { id: 4, x: 120, y: 100 },
  ];

  const getAgentAtDesk = (deskId) => {
    return agents.find(agent => agent.desk === deskId);
  };

  return (
    <div className="work-zone">
      {desks.map(desk => {
        const agent = getAgentAtDesk(desk.id);
        return (
          <div 
            key={desk.id} 
            className="desk-unit"
            style={{ left: desk.x, top: desk.y }}
          >
            <div className="pixel-desk desk">
              <div className="desk-top">
                <div className="pixel-computer monitor">
                  <div className="screen-glow"></div>
                </div>
              </div>
            </div>
            <div className="pixel-chair chair"></div>
            {agent && <AgentSprite agent={agent} />}
          </div>
        );
      })}
      <div className="floor-details">
        <div className="floor-tile tile-1"></div>
        <div className="floor-tile tile-2"></div>
        <div className="floor-tile tile-3"></div>
        <div className="floor-tile tile-4"></div>
      </div>
    </div>
  );
}

export default WorkZone;
