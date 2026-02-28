import { useState, useEffect } from 'react';
import './Agent.css';

const STATE_LABELS = {
  running: 'Работает',
  idle: 'Ожидает',
  waiting: 'Ждёт',
  error: 'Ошибка',
  meeting: 'На встрече',
};

function AgentInfo({ agent }) {
  const [timeInState, setTimeInState] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setTimeInState(prev => prev + 1);
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!agent) {
    return (
      <div className="agent-info empty">
        <span className="empty-text">Выберите агента</span>
      </div>
    );
  }

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="agent-info">
      <div className="agent-info-header">
        <div 
          className="agent-avatar" 
          style={{ backgroundColor: agent.color }}
        >
          {agent.name?.charAt(0).toUpperCase()}
        </div>
        <div className="agent-info-name">{agent.name}</div>
      </div>
      
      <div className="agent-info-details">
        <div className="info-row">
          <span className="info-label">Состояние</span>
          <span className={`info-value state ${agent.state}`}>
            <span className={`state-dot ${agent.state}`}></span>
            {STATE_LABELS[agent.state] || agent.state}
          </span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Комната</span>
          <span className="info-value">{agent.room}</span>
        </div>
        
        <div className="info-row">
          <span className="info-label">Время в состоянии</span>
          <span className="info-value time">{formatTime(timeInState)}</span>
        </div>
        
        {agent.task && (
          <div className="info-row task-row">
            <span className="info-label">Задача</span>
            <span className="info-value task">{agent.task}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentInfo;
