import React, { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, OrthographicCamera, ContactShadows } from '@react-three/drei';
import AgentSprite from './AgentSprite';
import { Html } from '@react-three/drei';

function OfficeFloor() {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.5, 0]}>
      <planeGeometry args={[20, 20]} />
      <meshStandardMaterial color="#1e293b" />
      <gridHelper args={[20, 20, "#475569", "#334155"]} rotation={[Math.PI / 2, 0, 0]} />
    </mesh>
  );
}

function RoomBox({ position, size, color, name }) {
  return (
    <group position={position}>
      <mesh position={[0, size[1] / 2 - 0.5, 0]}>
        <boxGeometry args={size} />
        <meshStandardMaterial color={color} transparent opacity={0.2} />
      </mesh>
      {/* Стены (L-shape) */}
      <mesh position={[-size[0] / 2, size[1] / 2 - 0.5, 0]}>
        <boxGeometry args={[0.1, size[1], size[2]]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <mesh position={[0, size[1] / 2 - 0.5, -size[2] / 2]}>
        <boxGeometry args={[size[0], size[1], 0.1]} />
        <meshStandardMaterial color={color} />
      </mesh>
      <Html position={[0, size[1], 0]} center>
        <div className="room-label-3d">{name}</div>
      </Html>
    </group>
  );
}

function Agent3D({ agent }) {
  // Простая логика позиционирования агента в зависимости от комнаты
  const roomPositions = {
    'work_zone': [-4, 0, -4],
    'meeting_room': [4, 0, -4],
    'kitchen': [-4, 0, 4],
    'game_room': [4, 0, 4],
    'boss_office': [0, 0, 0],
  };

  const basePos = roomPositions[agent.room] || [0, 0, 0];
  // Добавим немного рандома внутри комнаты
  const pos = [basePos[0] + (agent.id % 3), 0.5, basePos[2] + (agent.id % 2)];

  return (
    <group position={pos}>
      <Html center>
        <AgentSprite agent={agent} />
      </Html>
    </group>
  );
}

function Office({ agents = [], onAgentClick }) {
  return (
    <div style={{ width: '100%', height: '100%', background: '#0f172a' }}>
      <Canvas shadows>
        <OrthographicCamera
          makeDefault
          zoom={50}
          position={[10, 10, 10]}
          near={0.1}
          far={1000}
        />
        <OrbitControls 
          enablePan={true} 
          enableZoom={true} 
          minZoom={20} 
          maxZoom={100}
          maxPolarAngle={Math.PI / 2.1}
        />
        
        <ambientLight intensity={0.8} />
        <pointLight position={[10, 10, 10]} intensity={1} castShadow />
        <spotLight position={[-10, 10, 10]} angle={0.15} penumbra={1} intensity={1} />

        <Suspense fallback={null}>
          <OfficeFloor />
          
          <RoomBox position={[-5, 0, -5]} size={[8, 3, 8]} color="#0c4a6e" name="Work Zone" />
          <RoomBox position={[5, 0, -5]} size={[8, 3, 8]} color="#312e81" name="Meeting" />
          <RoomBox position={[-5, 0, 5]} size={[8, 3, 8]} color="#78350f" name="Kitchen" />
          <RoomBox position={[5, 0, 5]} size={[8, 3, 8]} color="#701a75" name="Game Room" />
          <RoomBox position={[0, 0, 0]} size={[4, 4, 4]} color="#450a0a" name="CEO" />

          {agents.map(agent => (
            <Agent3D key={agent.id} agent={agent} />
          ))}

          <ContactShadows opacity={0.4} scale={20} blur={2.4} far={4.5} />
        </Suspense>
      </Canvas>
    </div>
  );
}

export default Office;
