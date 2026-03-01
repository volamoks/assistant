import { TILE_SIZE, COLORS, AGENT_COLORS, STATE_COLORS } from '../constants.js';

export function drawAgent(ctx, agent, time) {
    const px = agent.x * TILE_SIZE;
    const py = agent.y * TILE_SIZE;

    // Animation offsets
    const bounce = Math.sin(time / 100 + agent.id.charCodeAt(0)) * 2;
    const walkOffset = agent.moving ? Math.sin(time / 50) * 3 : 0;

    // Draw shadow
    drawShadow(ctx, px, py);

    // Get agent appearance
    const shirtColor = AGENT_COLORS[agent.id] || COLORS.shirtMain;
    const drawY = py + bounce;

    // Draw based on activity
    if (agent.sitting) {
        drawSittingAgent(ctx, px, drawY, shirtColor, agent);
    } else if (agent.drinking) {
        drawDrinkingAgent(ctx, px, drawY, shirtColor, agent, time);
    } else {
        drawStandingAgent(ctx, px, drawY, shirtColor, agent, walkOffset);
    }

    // Draw status indicator
    drawStatusIndicator(ctx, px, drawY, agent.state);

    // Draw name label
    drawNameLabel(ctx, px, drawY, agent.name);
}

function drawShadow(ctx, px, py) {
    ctx.fillStyle = COLORS.shadow;
    ctx.beginPath();
    ctx.ellipse(px + 16, py + 28, 10, 4, 0, 0, Math.PI * 2);
    ctx.fill();
}

function drawStandingAgent(ctx, px, drawY, shirtColor, agent, walkOffset) {
    // Legs
    ctx.fillStyle = COLORS.pants;
    if (agent.moving) {
        ctx.fillRect(px + 10 + walkOffset, drawY + 20, 5, 8);
        ctx.fillRect(px + 17 - walkOffset, drawY + 20, 5, 8);
    } else {
        ctx.fillRect(px + 10, drawY + 20, 5, 8);
        ctx.fillRect(px + 17, drawY + 20, 5, 8);
    }

    // Body
    ctx.fillStyle = shirtColor;
    ctx.fillRect(px + 8, drawY + 10, 16, 12);

    // Head
    ctx.fillStyle = COLORS.skin;
    ctx.fillRect(px + 10, drawY + 2, 12, 10);

    // Eyes
    drawEyes(ctx, px, drawY, agent.direction);

    // Hair
    ctx.fillStyle = '#4a4a4a';
    ctx.fillRect(px + 10, drawY, 12, 4);
}

function drawSittingAgent(ctx, px, drawY, shirtColor, agent) {
    // For sitting, agent is lower
    const sitY = drawY + 8;

    // Legs (sticking forward)
    ctx.fillStyle = COLORS.pants;
    if (agent.facing === 'left') {
        ctx.fillRect(px + 4, sitY + 18, 8, 5);
    } else if (agent.facing === 'right') {
        ctx.fillRect(px + 20, sitY + 18, 8, 5);
    } else {
        ctx.fillRect(px + 10, sitY + 22, 5, 4);
        ctx.fillRect(px + 17, sitY + 22, 5, 4);
    }

    // Body (compressed)
    ctx.fillStyle = shirtColor;
    ctx.fillRect(px + 8, sitY + 8, 16, 12);

    // Arms (typing if working)
    if (agent.typing) {
        ctx.fillStyle = COLORS.skin;
        ctx.fillRect(px + 4, sitY + 12, 4, 8);
        ctx.fillRect(px + 24, sitY + 12, 4, 8);
    }

    // Head
    ctx.fillStyle = COLORS.skin;
    ctx.fillRect(px + 10, sitY, 12, 10);

    // Eyes
    drawEyes(ctx, px, sitY, agent.facing || 'down');

    // Hair
    ctx.fillStyle = '#4a4a4a';
    ctx.fillRect(px + 10, sitY - 2, 12, 4);
}

function drawDrinkingAgent(ctx, px, drawY, shirtColor, agent, time) {
    // Standing but with cup
    const armRaise = Math.sin(time / 200) * 3;

    // Legs
    ctx.fillStyle = COLORS.pants;
    ctx.fillRect(px + 10, drawY + 20, 5, 8);
    ctx.fillRect(px + 17, drawY + 20, 5, 8);

    // Body
    ctx.fillStyle = shirtColor;
    ctx.fillRect(px + 8, drawY + 10, 16, 12);

    // Head
    ctx.fillStyle = COLORS.skin;
    ctx.fillRect(px + 10, drawY + 2, 12, 10);

    // Arm with cup
    ctx.fillStyle = COLORS.skin;
    ctx.fillRect(px + 22, drawY + 10 - armRaise, 4, 10 + armRaise);

    // Cup
    ctx.fillStyle = '#fff';
    ctx.fillRect(px + 21, drawY + 6 - armRaise, 6, 6);
    ctx.fillStyle = 'rgba(255,255,255,0.5)';
    ctx.fillRect(px + 22, drawY + 4 - armRaise, 2, 2);

    // Eyes
    drawEyes(ctx, px, drawY, 'down');

    // Hair
    ctx.fillStyle = '#4a4a4a';
    ctx.fillRect(px + 10, drawY, 12, 4);
}

function drawEyes(ctx, px, drawY, direction) {
    ctx.fillStyle = '#000';
    if (direction === 'right') {
        ctx.fillRect(px + 18, drawY + 5, 2, 2);
    } else if (direction === 'left') {
        ctx.fillRect(px + 12, drawY + 5, 2, 2);
    } else {
        ctx.fillRect(px + 13, drawY + 5, 2, 2);
        ctx.fillRect(px + 17, drawY + 5, 2, 2);
    }
}

function drawStatusIndicator(ctx, px, drawY, state) {
    let statusColor = STATE_COLORS[state] || STATE_COLORS.idle;

    ctx.fillStyle = statusColor;
    ctx.beginPath();
    ctx.moveTo(px + 16, drawY - 8);
    ctx.lineTo(px + 20, drawY - 2);
    ctx.lineTo(px + 16, drawY);
    ctx.lineTo(px + 12, drawY - 2);
    ctx.closePath();
    ctx.fill();
}

function drawNameLabel(ctx, px, drawY, name) {
    ctx.fillStyle = '#fff';
    ctx.font = '10px monospace';
    ctx.textAlign = 'center';
    ctx.fillText(name.split(' ')[0], px + 16, drawY - 12);
}

// Update agent positions based on their state
export function updateAgentBehaviors(agents, workSpots, idleSpots, time) {
    return agents.map(agent => {
        const updated = { ...agent };

        // Determine behavior based on state
        switch (agent.state) {
            case 'running':
            case 'working':
                // Find work spot for this agent
                const workSpot = findSpotForAgent(agent, workSpots);
                if (workSpot) {
                    updated.x = workSpot.x;
                    updated.y = workSpot.y;
                    updated.sitting = true;
                    updated.facing = workSpot.facing;
                    updated.typing = true;
                }
                break;

            case 'meeting':
                const meetingSpot = findSpotForAgent(agent, workSpots.filter(s => s.type === 'meeting'));
                if (meetingSpot) {
                    updated.x = meetingSpot.x;
                    updated.y = meetingSpot.y;
                    updated.sitting = true;
                    updated.facing = meetingSpot.facing;
                    updated.typing = false;
                }
                break;

            case 'idle':
                // Random idle behavior
                const idleSeed = Math.floor(time / 5000) + agent.id.charCodeAt(0);
                const idleType = idleSeed % 3;

                if (idleType === 0) {
                    // Coffee break
                    const coffeeSpot = idleSpots.find(s => s.type === 'coffee');
                    if (coffeeSpot) {
                        updated.x = coffeeSpot.x;
                        updated.y = coffeeSpot.y;
                        updated.drinking = true;
                        updated.sitting = false;
                    }
                } else if (idleType === 1) {
                    // Relax on couch
                    const relaxSpot = idleSpots.find(s => s.type === 'relax');
                    if (relaxSpot) {
                        updated.x = relaxSpot.x;
                        updated.y = relaxSpot.y;
                        updated.sitting = true;
                        updated.facing = relaxSpot.facing;
                    }
                } else {
                    // Walking around
                    const walkSpot = idleSpots.find(s => s.type === 'walk' && (s.x + s.y) % 5 === idleSeed % 5);
                    if (walkSpot) {
                        updated.x = walkSpot.x;
                        updated.y = walkSpot.y;
                        updated.moving = true;
                        updated.sitting = false;
                    }
                }
                break;

            case 'waiting':
                // Stand near their assigned room
                const roomSpot = findSpotForAgent(agent, workSpots);
                if (roomSpot) {
                    updated.x = roomSpot.x + 1;
                    updated.y = roomSpot.y;
                    updated.sitting = false;
                    updated.moving = false;
                }
                break;

            default:
                // Default to room center
                updated.sitting = false;
        }

        return updated;
    });
}

function findSpotForAgent(agent, spots) {
    // Simple hash to assign consistent spot per agent
    const index = agent.id.charCodeAt(0) % spots.length;
    return spots[index];
}