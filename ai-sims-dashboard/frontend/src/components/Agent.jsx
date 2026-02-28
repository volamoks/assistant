import { useState } from 'react';
import AgentSprite from './AgentSprite';
import './Agent.css';

function Agent({ id, name, color, state = 'idle', room, task }) {
  const [showTooltip, setShowTooltip] = useState(false);

  return (
    <div 
      className={`agent-container ${state}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <AgentSprite state={state} color={color} />
      
      {showTooltip && (
        <div className="agent-tooltip">
          <div className="tooltip-name">{name}</div>
          <div className="tooltip-state">
            <span className={`state-dot ${state}`}></span>
            {state}
          </div>
          {task && <div className="tooltip-task">{task}</div>}
        </div>
      )}
    </div>
  );
}

export default Agent;
