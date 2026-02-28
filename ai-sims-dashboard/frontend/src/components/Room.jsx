import React from 'react';
import './Room.css';

const roomConfigs = {
  work_zone: {
    name: 'Work Zone',
    icon: '💻',
    color: '#0f3460',
  },
  game_room: {
    name: 'Game Room',
    icon: '🎮',
    color: '#6b2d5c',
  },
  kitchen: {
    name: 'Kitchen',
    icon: '🍳',
    color: '#4a4a0f',
  },
  meeting_room: {
    name: 'Meeting',
    icon: '📋',
    color: '#0f4a4a',
  },
  boss_office: {
    name: 'Boss Office',
    icon: '👔',
    color: '#6b2d2d',
  },
};

function Room({ type = 'work_zone', agents = [] }) {
  const config = roomConfigs[type] || roomConfigs.work_zone;

  return (
    <div className={`room ${type}`}>
      <div className="room-floor"></div>
      <div className="room-walls">
        <div className="wall wall-left"></div>
        <div className="wall wall-right"></div>
      </div>
      <div className="room-content">
        <div className="room-icon">{config.icon}</div>
      </div>
      <div className="room-agent-count">
        {agents.length > 0 && (
          <span className="agent-badge">{agents.length}</span>
        )}
      </div>
    </div>
  );
}

export default Room;
