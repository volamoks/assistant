import { useState, useEffect, useCallback, useRef } from 'react';

const API_HOST = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
const API_URL = (API_HOST === 'localhost') ? 'http://localhost:8000/api' : `https://${API_HOST}/api`;
const WS_URL = (API_HOST === 'localhost') ? 'ws://localhost:8000/ws' : `wss://${API_HOST}/ws`;

export function useAgents() {
  const [agents, setAgents] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);

  // Fallback: Fetch via API if WS fails
  const fetchAgents = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/agents`);
      if (!response.ok) throw new Error('Failed to fetch');
      const data = await response.json();
      setAgents(data);
      setIsConnected(true);
      setError(null);
    } catch (err) {
      console.error('API Poll Error:', err);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchAgents();

    // Setup WebSocket
    const connectWS = () => {
      console.log('🔌 Connecting to WebSocket:', WS_URL);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Connected to WebSocket');
        setIsConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'agent_update' && message.data) {
            setAgents(message.data);
          }
        } catch (e) {
          console.error('WS Message Parse Error:', e);
        }
      };

      ws.onerror = (err) => {
        console.error('WS Connection Error:', err);
        setIsConnected(false);
      };

      ws.onclose = () => {
        console.log('🔌 WS Connection Closed. Reconnecting in 3s...');
        setIsConnected(false);
        setTimeout(connectWS, 3000); // Reconnect logic
      };
    };

    connectWS();

    // Fallback polling (every 10s) just in case
    const pollInterval = setInterval(fetchAgents, 10000);

    return () => {
      clearInterval(pollInterval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [fetchAgents]);

  return {
    agents,
    isConnected,
    error,
    refresh: fetchAgents,
  };
}

export default useAgents;
