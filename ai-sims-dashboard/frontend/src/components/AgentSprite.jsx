import './Agent.css';

const STATE_COLORS = {
  running: '#4ade80',
  idle: '#ffffff',
  waiting: '#facc15',
  error: '#ef4444',
  meeting: '#60a5fa',
};

function AgentSprite({ agent, state, color }) {
  const agentState = agent?.state || state || 'idle';
  const agentColor = agent?.color || color || '#8b5cf6';
  const borderColor = STATE_COLORS[agentState] || STATE_COLORS.idle;

  return (
    <div className="agent-terraria-wrapper">
      <div className="agent-shadow-oval"></div>
      
      {/* "Sims" Diamond - Floating above */}
      <div className="agent-plumbob" style={{ backgroundColor: borderColor }}></div>

      <div className={`agent-character ${agentState}`} style={{ '--agent-color': agentColor }}>
        {/* Head with more detail */}
        <div className="char-head">
          <div className="char-hair"></div>
          <div className="char-face">
            <div className="char-eye left"></div>
            <div className="char-eye right"></div>
            <div className="char-blush"></div>
          </div>
        </div>

        {/* Tall Torso like Terraria */}
        <div className="char-torso">
          <div className="char-arms">
            <div className="char-arm left"></div>
            <div className="char-arm right"></div>
          </div>
        </div>

        {/* Moving Legs */}
        <div className="char-legs">
          <div className="char-leg left"></div>
          <div className="char-leg right"></div>
        </div>
      </div>

      <div className="char-name-label">{agent?.name?.split(' ')[0]}</div>
    </div>
  );
}

export default AgentSprite;
