import { TILE_SIZE, COLORS } from '../constants.js';
import { drawPixelRect } from './tiles.js';

export function drawFurniture(ctx, item, particlesRef) {
    const px = item.x * TILE_SIZE;
    const py = item.y * TILE_SIZE;

    switch (item.type) {
        case 'desk':
            drawDesk(ctx, px, py);
            break;
        case 'computer':
            drawComputer(ctx, px, py);
            break;
        case 'chair':
            drawChair(ctx, px, py, item.facing);
            break;
        case 'plant':
            drawPlant(ctx, px, py);
            break;
        case 'couch':
            drawCouch(ctx, px, py);
            break;
        case 'tv':
            drawTV(ctx, px, py);
            break;
        case 'coffee':
            drawCoffee(ctx, px, py, particlesRef);
            break;
        case 'fridge':
            drawFridge(ctx, px, py);
            break;
        case 'big_table':
            drawBigTable(ctx, px, py);
            break;
        case 'big_desk':
            drawBigDesk(ctx, px, py);
            break;
        case 'bookshelf':
            drawBookshelf(ctx, px, py);
            break;
        case 'whiteboard':
            drawWhiteboard(ctx, px, py);
            break;
        case 'lamp':
            drawLamp(ctx, px, py);
            break;
        case 'rug':
            drawRug(ctx, px, py);
            break;
        case 'printer':
            drawPrinter(ctx, px, py);
            break;
        case 'trash':
            drawTrash(ctx, px, py);
            break;
        case 'clock':
            drawClock(ctx, px, py);
            break;
        case 'window':
            drawWindow(ctx, px, py);
            break;
        case 'painting':
            drawPainting(ctx, px, py);
            break;
        case 'poster':
            drawPoster(ctx, px, py);
            break;
        case 'table':
            drawTable(ctx, px, py);
            break;
        case 'boss_chair':
            drawBossChair(ctx, px, py);
            break;
    }
}

function drawDesk(ctx, px, py) {
    drawPixelRect(ctx, px, py, TILE_SIZE, TILE_SIZE - 8, COLORS.desk);
    drawPixelRect(ctx, px + 2, py + TILE_SIZE - 8, 4, 8, COLORS.desk);
    drawPixelRect(ctx, px + TILE_SIZE - 6, py + TILE_SIZE - 8, 4, 8, COLORS.desk);
}

function drawComputer(ctx, px, py) {
    // Monitor
    drawPixelRect(ctx, px + 8, py + 4, 16, 12, COLORS.computer);
    // Screen
    drawPixelRect(ctx, px + 10, py + 6, 12, 8, COLORS.screenOn);
    // Stand
    drawPixelRect(ctx, px + 14, py + 16, 4, 8, COLORS.computer);
    // Glow
    ctx.fillStyle = 'rgba(0,206,209,0.2)';
    ctx.fillRect(px + 6, py + 2, 20, 16);
}

function drawChair(ctx, px, py, facing) {
    drawPixelRect(ctx, px + 4, py + 12, 24, 12, COLORS.chair);
    if (facing === 'left' || facing === 'right') {
        drawPixelRect(ctx, px + (facing === 'left' ? 20 : 4), py + 4, 8, 20, COLORS.chair);
    } else {
        drawPixelRect(ctx, px + 4, py + (facing === 'up' ? 20 : 4), 24, 8, COLORS.chair);
    }
}

function drawPlant(ctx, px, py) {
    drawPixelRect(ctx, px + 8, py + 18, 16, 10, COLORS.pot);
    ctx.fillStyle = COLORS.plant;
    ctx.beginPath();
    ctx.arc(px + 16, py + 12, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(px + 12, py + 10, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(px + 20, py + 10, 6, 0, Math.PI * 2);
    ctx.fill();
}

function drawCouch(ctx, px, py) {
    drawPixelRect(ctx, px, py + 8, TILE_SIZE * 2, 20, COLORS.couch);
    drawPixelRect(ctx, px, py + 4, TILE_SIZE * 2, 8, COLORS.couch);
    drawPixelRect(ctx, px, py + 8, 6, 16, COLORS.couch);
    drawPixelRect(ctx, px + TILE_SIZE * 2 - 6, py + 8, 6, 16, COLORS.couch);
}

function drawTV(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 20, 24, 8, COLORS.desk);
    drawPixelRect(ctx, px, py + 4, TILE_SIZE, 16, '#1a1a1a');
    drawPixelRect(ctx, px + 4, py + 8, TILE_SIZE - 8, 10, COLORS.screenOn);
}

function drawCoffee(ctx, px, py, particlesRef) {
    drawPixelRect(ctx, px + 4, py + 4, 24, 24, COLORS.coffee);
    drawPixelRect(ctx, px + 10, py + 12, 12, 10, '#000');
    if (Math.random() > 0.7 && particlesRef) {
        particlesRef.current.push({
            x: px + 16,
            y: py + 8,
            vx: (Math.random() - 0.5) * 0.5,
            vy: -0.5 - Math.random() * 0.5,
            life: 60,
            color: 'rgba(255,255,255,0.5)',
            size: 2
        });
    }
}

function drawFridge(ctx, px, py) {
    drawPixelRect(ctx, px, py, TILE_SIZE, TILE_SIZE, '#E8E8E8');
    ctx.strokeStyle = '#999';
    ctx.strokeRect(px + 2, py + 2, TILE_SIZE - 4, TILE_SIZE - 4);
    drawPixelRect(ctx, px + TILE_SIZE - 6, py + 10, 3, 8, '#666');
}

function drawBigTable(ctx, px, py) {
    drawPixelRect(ctx, px, py + 8, TILE_SIZE * 2, 16, COLORS.desk);
    drawPixelRect(ctx, px + 4, py + 24, 4, 8, COLORS.desk);
    drawPixelRect(ctx, px + TILE_SIZE * 2 - 8, py + 24, 4, 8, COLORS.desk);
}

function drawBigDesk(ctx, px, py) {
    drawPixelRect(ctx, px, py + 8, TILE_SIZE * 2, 20, '#654321');
    drawPixelRect(ctx, px + 8, py + 10, 6, 4, '#8B0000');
    drawPixelRect(ctx, px + 40, py + 10, 8, 6, '#FFD700');
}

function drawBookshelf(ctx, px, py) {
    drawPixelRect(ctx, px, py, TILE_SIZE, TILE_SIZE, COLORS.desk);
    drawPixelRect(ctx, px + 4, py + 4, 6, 12, '#8B0000');
    drawPixelRect(ctx, px + 12, py + 4, 5, 10, '#006400');
    drawPixelRect(ctx, px + 20, py + 4, 7, 14, '#00008B');
}

function drawWhiteboard(ctx, px, py) {
    drawPixelRect(ctx, px, py + 4, TILE_SIZE, 20, '#F5F5F5');
    ctx.strokeStyle = '#666';
    ctx.strokeRect(px, py + 4, TILE_SIZE, 20);
    ctx.fillStyle = '#333';
    ctx.fillRect(px + 4, py + 10, 20, 2);
    ctx.fillRect(px + 4, py + 14, 16, 2);
}

function drawLamp(ctx, px, py) {
    drawPixelRect(ctx, px + 12, py + 24, 8, 4, '#444');
    drawPixelRect(ctx, px + 15, py + 12, 2, 12, '#444');
    drawPixelRect(ctx, px + 8, py + 4, 16, 10, '#FFD700');
    ctx.fillStyle = 'rgba(255,215,0,0.3)';
    ctx.fillRect(px - 8, py - 8, TILE_SIZE + 16, TILE_SIZE + 16);
}

function drawRug(ctx, px, py) {
    ctx.fillStyle = '#8B008B';
    ctx.fillRect(px + 4, py + 4, TILE_SIZE - 8, TILE_SIZE - 8);
    ctx.strokeStyle = '#FFD700';
    ctx.strokeRect(px + 6, py + 6, TILE_SIZE - 12, TILE_SIZE - 12);
}

function drawPrinter(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 8, 24, 16, '#666');
    drawPixelRect(ctx, px + 8, py + 12, 16, 8, '#333');
    drawPixelRect(ctx, px + 12, py + 4, 8, 4, '#fff');
}

function drawTrash(ctx, px, py) {
    drawPixelRect(ctx, px + 8, py + 8, 16, 20, '#444');
    drawPixelRect(ctx, px + 6, py + 6, 20, 4, '#333');
    ctx.strokeStyle = '#666';
    ctx.beginPath();
    ctx.moveTo(px + 10, py + 12);
    ctx.lineTo(px + 10, py + 24);
    ctx.moveTo(px + 16, py + 12);
    ctx.lineTo(px + 16, py + 24);
    ctx.moveTo(px + 22, py + 12);
    ctx.lineTo(px + 22, py + 24);
    ctx.stroke();
}

function drawClock(ctx, px, py) {
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(px + 16, py + 16, 12, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#333';
    ctx.fillRect(px + 15, py + 8, 2, 8);
    ctx.fillRect(px + 16, py + 15, 6, 2);
}

function drawWindow(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 4, 24, 24, '#87CEEB');
    drawPixelRect(ctx, px + 14, py + 4, 4, 24, '#fff');
    drawPixelRect(ctx, px + 4, py + 14, 24, 4, '#fff');
    ctx.strokeStyle = '#fff';
    ctx.strokeRect(px + 4, py + 4, 24, 24);
}

function drawPainting(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 4, 24, 20, '#8B4513');
    drawPixelRect(ctx, px + 6, py + 6, 20, 16, '#FFD700');
    ctx.fillStyle = '#4169E1';
    ctx.beginPath();
    ctx.arc(px + 16, py + 14, 6, 0, Math.PI * 2);
    ctx.fill();
}

function drawPoster(ctx, px, py) {
    drawPixelRect(ctx, px + 8, py + 4, 16, 20, '#fff');
    ctx.fillStyle = '#FF6347';
    ctx.fillRect(px + 10, py + 8, 12, 4);
    ctx.fillStyle = '#32CD32';
    ctx.fillRect(px + 10, py + 14, 12, 4);
    ctx.fillStyle = '#4169E1';
    ctx.fillRect(px + 10, py + 20, 12, 2);
}

function drawTable(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 8, 24, 12, COLORS.desk);
    drawPixelRect(ctx, px + 6, py + 20, 4, 8, COLORS.desk);
    drawPixelRect(ctx, px + 22, py + 20, 4, 8, COLORS.desk);
}

function drawBossChair(ctx, px, py) {
    drawPixelRect(ctx, px + 4, py + 8, 24, 20, '#4a0000');
    drawPixelRect(ctx, px + 4, py + 4, 24, 8, '#4a0000');
    drawPixelRect(ctx, px + 6, py + 12, 4, 4, '#FFD700');
}