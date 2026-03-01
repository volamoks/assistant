import React, { useEffect, useRef, useCallback } from 'react';
import { TILE_SIZE, GRID_WIDTH, GRID_HEIGHT, ROOMS, FURNITURE, WORK_SPOTS, IDLE_SPOTS } from './constants.js';
import { drawRoom, drawFurniture, drawAgent, drawParticles, updateAgentBehaviors } from './drawing/index.js';
import './CanvasOffice.css';

function CanvasOffice({ agents = [], onAgentClick }) {
    const canvasRef = useRef(null);
    const animationRef = useRef(null);
    const agentsRef = useRef([]);
    const particlesRef = useRef([]);

    // Initialize agents with positions
    useEffect(() => {
        agentsRef.current = agents.map(agent => ({
            ...agent,
            x: 12,
            y: 8,
            sitting: false,
            drinking: false,
            typing: false,
            moving: false,
            facing: 'down'
        }));
    }, [agents]);

    // Main render loop
    const render = useCallback((time) => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');

        // Clear canvas
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Draw all rooms
        ROOMS.forEach(room => drawRoom(ctx, room));

        // Draw furniture
        FURNITURE.forEach(item => drawFurniture(ctx, item, particlesRef));

        // Update and draw agents with behaviors
        agentsRef.current = updateAgentBehaviors(agentsRef.current, WORK_SPOTS, IDLE_SPOTS, time);

        // Sort agents by Y for depth
        const sortedAgents = [...agentsRef.current].sort((a, b) => a.y - b.y);
        sortedAgents.forEach(agent => drawAgent(ctx, agent, time));

        // Draw particles
        drawParticles(ctx, particlesRef);

        // Draw room labels
        drawRoomLabels(ctx);

        animationRef.current = requestAnimationFrame(render);
    }, []);

    function drawRoomLabels(ctx) {
        ctx.fillStyle = 'rgba(255,255,255,0.8)';
        ctx.font = 'bold 12px monospace';
        ctx.textAlign = 'center';
        ROOMS.forEach(room => {
            const cx = (room.x + room.w / 2) * TILE_SIZE;
            const cy = (room.y + room.h / 2) * TILE_SIZE;
            ctx.fillText(room.name, cx, cy);
        });
    }

    // Handle click
    const handleClick = (e) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const x = Math.floor((e.clientX - rect.left) / TILE_SIZE);
        const y = Math.floor((e.clientY - rect.top) / TILE_SIZE);

        const clickedAgent = agentsRef.current.find(agent =>
            Math.abs(agent.x - x) < 1 && Math.abs(agent.y - y) < 1
        );

        if (clickedAgent && onAgentClick) {
            onAgentClick(clickedAgent);
        }
    };

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        canvas.width = GRID_WIDTH * TILE_SIZE;
        canvas.height = GRID_HEIGHT * TILE_SIZE;

        animationRef.current = requestAnimationFrame(render);

        return () => {
            if (animationRef.current) {
                cancelAnimationFrame(animationRef.current);
            }
        };
    }, [render]);

    return (
        <div className="canvas-office-container">
            <canvas
                ref={canvasRef}
                className="canvas-office"
                onClick={handleClick}
            />
        </div>
    );
}

export default CanvasOffice;