import { TILE_SIZE } from '../constants.js';

export function drawPixelRect(ctx, x, y, w, h, color) {
    ctx.fillStyle = color;
    ctx.fillRect(x, y, w, h);
}

export function drawPixelCircle(ctx, x, y, r, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
}

export function drawTile(ctx, x, y, color, type = 'floor') {
    const px = x * TILE_SIZE;
    const py = y * TILE_SIZE;

    // Base tile
    drawPixelRect(ctx, px, py, TILE_SIZE, TILE_SIZE, color);

    // Tile detail based on type
    if (type === 'floor') {
        // Wood grain effect
        ctx.fillStyle = 'rgba(0,0,0,0.1)';
        ctx.fillRect(px + 4, py + 8, TILE_SIZE - 8, 2);
        ctx.fillRect(px + 2, py + 20, TILE_SIZE - 4, 2);
    } else if (type === 'carpet') {
        // Carpet pattern
        ctx.fillStyle = 'rgba(255,255,255,0.1)';
        ctx.fillRect(px + 8, py + 8, 4, 4);
        ctx.fillRect(px + 20, py + 20, 4, 4);
    } else if (type === 'tile') {
        // Tile grid
        ctx.strokeStyle = 'rgba(0,0,0,0.2)';
        ctx.strokeRect(px, py, TILE_SIZE, TILE_SIZE);
    }

    // Tile border
    ctx.strokeStyle = 'rgba(0,0,0,0.1)';
    ctx.strokeRect(px, py, TILE_SIZE, TILE_SIZE);
}

export function drawWall(ctx, x, y, color) {
    const px = x * TILE_SIZE;
    const py = y * TILE_SIZE;

    // Wall base
    drawPixelRect(ctx, px, py - 8, TILE_SIZE, TILE_SIZE + 8, color);

    // Wall highlight
    ctx.fillStyle = 'rgba(255,255,255,0.1)';
    ctx.fillRect(px, py - 8, TILE_SIZE, 4);

    // Wall shadow
    ctx.fillStyle = 'rgba(0,0,0,0.3)';
    ctx.fillRect(px, py + TILE_SIZE - 8, TILE_SIZE, 8);
}

export function drawRoom(ctx, room) {
    // Draw floor tiles
    for (let x = room.x; x < room.x + room.w; x++) {
        for (let y = room.y; y < room.y + room.h; y++) {
            let tileType = 'floor';
            if (room.id === 'meeting' || room.id === 'boss_office') tileType = 'carpet';
            if (room.id === 'kitchen') tileType = 'tile';
            drawTile(ctx, x, y, room.color, tileType);
        }
    }

    // Draw walls (top and left edges)
    for (let x = room.x; x < room.x + room.w; x++) {
        drawWall(ctx, x, room.y, room.wall);
    }
    for (let y = room.y; y < room.y + room.h; y++) {
        drawWall(ctx, room.x, y, room.wall);
    }
}