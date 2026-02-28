import React from 'react';
import AgentSprite from './AgentSprite';
import './MeetingRoom.css';

function MeetingRoom({ agents = [] }) {
  const seats = [
    { id: 1, x: 30, y: 40 },
    { id: 2, x: 80, y: 20 },
    { id: 3, x: 130, y: 40 },
    { id: 4, x: 30, y: 100 },
    { id: 5, x: 80, y: 120 },
    { id: 6, x: 130, y: 100 },
  ];

  const getAgentAtSeat = (seatId) => {
    return agents.find(agent => agent.seat === seatId);
  };

  return (
    <div className="meeting-room">
      {/* Большой стол */}
      <div className="meeting-table">
        <div className="table-main">
          <div className="table-surface"></div>
        </div>
        <div className="table-leg leg-center"></div>
      </div>

      {/* Доска */}
      <div className="whiteboard-unit" style={{ left: 20, top: 10 }}>
        <div className="pixel-whiteboard board">
          <div className="board-frame">
            <div className="board-surface">
              <div className="board-text">📋</div>
            </div>
          </div>
          <div className="board-stand"></div>
        </div>
      </div>

      {/* Стулья вокруг стола */}
      {seats.map(seat => {
        const agent = getAgentAtSeat(seat.id);
        return (
          <div 
            key={seat.id}
            className="seat-unit"
            style={{ left: seat.x, top: seat.y }}
          >
            <div className="meeting-chair">
              <div className="chair-seat"></div>
              <div className="chair-back"></div>
            </div>
            {agent && <AgentSprite agent={agent} />}
          </div>
        );
      })}
    </div>
  );
}

export default MeetingRoom;
