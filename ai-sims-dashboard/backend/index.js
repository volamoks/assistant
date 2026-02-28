import express from 'express';
import cors from 'cors';
import { WebSocketServer } from 'ws';

const app = express();
const PORT = 8000;

// Middleware
app.use(cors());
app.use(express.json());

// Mock agent data
const agents = [
  { id: 'main', name: 'Main Agent', color: '#9B59B6', state: 'waiting', room: 'boss_office', task: null },
  { id: 'coder', name: 'Coder', color: '#3498DB', state: 'running', room: 'work_zone', task: 'coding' },
  { id: 'researcher', name: 'Researcher', color: '#2ECC71', state: 'idle', room: 'work_zone', task: null },
  { id: 'analyst', name: 'Analyst', color: '#F1C40F', state: 'waiting', room: 'work_zone', task: null }
];

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Get all agents
app.get('/api/agents', (req, res) => {
  res.json(agents);
});

// Create HTTP server
const server = app.listen(PORT, () => {
  console.log(`🚀 AI Sims Backend running on http://localhost:${PORT}`);
});

// WebSocket server
const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws) => {
  console.log('🔌 Client connected to WebSocket');
  
  // Send immediate update on connect
  ws.send(JSON.stringify({ type: 'agent_update', data: agents }));
  
  ws.on('close', () => {
    console.log('🔌 Client disconnected');
  });
});

// Broadcast updates every 5 seconds
setInterval(() => {
  // Randomly update some agent states for demo
  const updatedAgents = agents.map(agent => ({
    ...agent,
    state: Math.random() > 0.7 ? (agent.state === 'running' ? 'idle' : 'running') : agent.state
  }));
  
  const message = JSON.stringify({ type: 'agent_update', data: updatedAgents });
  
  wss.clients.forEach((client) => {
    if (client.readyState === 1) { // WebSocket.OPEN
      client.send(message);
    }
  });
}, 5000);

console.log('📡 WebSocket server running on ws://localhost:' + PORT + '/ws');
