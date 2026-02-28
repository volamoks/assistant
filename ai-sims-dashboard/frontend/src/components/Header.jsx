import './Header.css';

function Header({ isConnected }) {
  return (
    <header className="dashboard-header">
      <div className="header-content">
        <h1 className="header-title">AI Sims Dashboard</h1>
        <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          <span className="status-text">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>
    </header>
  );
}

export default Header;
