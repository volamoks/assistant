import { useState, useEffect } from 'react';
import Header from './components/Header';
import CanvasOffice from './canvas/CanvasOffice';
import AgentInfo from './components/AgentInfo';
import useAgents from './hooks/useAgents';
import './App.css';

function App() {
  const { isConnected, agents } = useAgents();
  const [selectedAgent, setSelectedAgent] = useState(null);

  return (
    <div className="app immersive-mode">
      {/* Маленький плавающий индикатор подключения */}
      <div className="status-overlay">
        <div className={`status-dot ${isConnected ? 'online' : 'offline'}`}></div>
        <span className="status-text">{isConnected ? 'LIVE' : 'RECONNECTING...'}</span>
      </div>

      {/* Pixel-art офис в стиле Stardew Valley */}
      <main className="game-world">
        <CanvasOffice agents={agents} onAgentClick={setSelectedAgent} />
      </main>

      {/* Панель информации (выезжает при клике на агента) */}
      {selectedAgent && (
        <aside className="agent-detail-panel">
          <button className="close-panel" onClick={() => setSelectedAgent(null)}>×</button>
          <AgentInfo agent={selectedAgent} />
        </aside>
      )}

      {/* Список агентов внизу (как в играх выбор персонажа) */}
      <div className="agent-hotbar">
        {agents.map(agent => (
          <div
            key={agent.id}
            className={`hotbar-item ${selectedAgent?.id === agent.id ? 'active' : ''}`}
            onClick={() => setSelectedAgent(agent)}
            style={{ '--agent-color': agent.color }}
          >
            <div className="agent-mini-icon"></div>
            <span className="agent-short-name">{agent.name.split(' ')[0]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
