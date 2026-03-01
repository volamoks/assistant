// Canvas and grid settings
export const TILE_SIZE = 32;
export const GRID_WIDTH = 24;
export const GRID_HEIGHT = 16;

// Stardew Valley inspired color palette
export const COLORS = {
    // Floors
    floorWood: '#8B6914',
    floorWoodDark: '#6B4E0A',
    floorCarpet: '#8B4513',
    floorTile: '#696969',
    floorGrass: '#4CAF50',

    // Walls
    wallWood: '#A0522D',
    wallBrick: '#8B4513',
    wallModern: '#4682B4',
    wallCEO: '#2F4F4F',

    // Furniture
    desk: '#8B4513',
    chair: '#654321',
    computer: '#2F4F4F',
    screenOn: '#00CED1',
    screenOff: '#1a1a1a',
    plant: '#228B22',
    pot: '#8B4513',
    couch: '#4169E1',
    fridge: '#C0C0C0',
    coffee: '#4A3728',

    // Agents
    skin: '#FDBCB4',
    shirtMain: '#9B59B6',
    shirtCoder: '#3498DB',
    shirtResearcher: '#2ECC71',
    shirtAnalyst: '#F1C40F',
    pants: '#2C3E50',

    // Effects
    shadow: 'rgba(0,0,0,0.3)',
    highlight: 'rgba(255,255,255,0.2)',
};

// Room definitions
export const ROOMS = [
    { id: 'work_zone', x: 1, y: 1, w: 8, h: 6, color: COLORS.floorWood, wall: COLORS.wallWood, name: 'Work' },
    { id: 'meeting', x: 11, y: 1, w: 6, h: 6, color: COLORS.floorCarpet, wall: COLORS.wallModern, name: 'Meeting' },
    { id: 'kitchen', x: 1, y: 9, w: 6, h: 6, color: COLORS.floorTile, wall: COLORS.wallBrick, name: 'Kitchen' },
    { id: 'game_room', x: 9, y: 9, w: 6, h: 6, color: COLORS.floorWoodDark, wall: COLORS.wallModern, name: 'Game' },
    { id: 'boss_office', x: 17, y: 5, w: 6, h: 8, color: COLORS.floorCarpet, wall: COLORS.wallCEO, name: 'CEO' },
];

// Work spots - where agents sit when working
export const WORK_SPOTS = [
    // Work Zone desks
    { x: 2, y: 2, room: 'work_zone', type: 'computer', facing: 'right' },
    { x: 2, y: 5, room: 'work_zone', type: 'computer', facing: 'right' },
    { x: 6, y: 2, room: 'work_zone', type: 'computer', facing: 'left' },
    { x: 6, y: 5, room: 'work_zone', type: 'computer', facing: 'left' },

    // Meeting room seats
    { x: 12, y: 3, room: 'meeting', type: 'meeting', facing: 'right' },
    { x: 15, y: 3, room: 'meeting', type: 'meeting', facing: 'left' },
    { x: 13, y: 2, room: 'meeting', type: 'meeting', facing: 'down' },
    { x: 14, y: 2, room: 'meeting', type: 'meeting', facing: 'down' },
    { x: 13, y: 5, room: 'meeting', type: 'meeting', facing: 'up' },
    { x: 14, y: 5, room: 'meeting', type: 'meeting', facing: 'up' },

    // CEO desk
    { x: 19, y: 8, room: 'boss_office', type: 'boss', facing: 'down' },
];

// Idle spots - where agents go when idle
export const IDLE_SPOTS = [
    // Kitchen coffee
    { x: 3, y: 9, room: 'kitchen', type: 'coffee', facing: 'down' },
    { x: 2, y: 12, room: 'kitchen', type: 'sit', facing: 'down' },

    // Game room couch
    { x: 10, y: 10, room: 'game_room', type: 'relax', facing: 'right' },
    { x: 11, y: 10, room: 'game_room', type: 'relax', facing: 'right' },

    // Random walk points
    { x: 4, y: 4, room: 'work_zone', type: 'walk' },
    { x: 13, y: 4, room: 'meeting', type: 'walk' },
    { x: 4, y: 11, room: 'kitchen', type: 'walk' },
    { x: 11, y: 12, room: 'game_room', type: 'walk' },
    { x: 20, y: 8, room: 'boss_office', type: 'walk' },
];

// Furniture definitions
export const FURNITURE = [
    // Work Zone
    { type: 'desk', x: 2, y: 2, room: 'work_zone', facing: 'right' },
    { type: 'computer', x: 2, y: 2, room: 'work_zone' },
    { type: 'chair', x: 3, y: 2, room: 'work_zone', facing: 'left' },
    { type: 'desk', x: 2, y: 5, room: 'work_zone', facing: 'right' },
    { type: 'computer', x: 2, y: 5, room: 'work_zone' },
    { type: 'chair', x: 3, y: 5, room: 'work_zone', facing: 'left' },
    { type: 'desk', x: 6, y: 2, room: 'work_zone', facing: 'left' },
    { type: 'computer', x: 6, y: 2, room: 'work_zone' },
    { type: 'chair', x: 5, y: 2, room: 'work_zone', facing: 'right' },
    { type: 'desk', x: 6, y: 5, room: 'work_zone', facing: 'left' },
    { type: 'computer', x: 6, y: 5, room: 'work_zone' },
    { type: 'chair', x: 5, y: 5, room: 'work_zone', facing: 'right' },
    { type: 'plant', x: 1, y: 3, room: 'work_zone' },
    { type: 'plant', x: 7, y: 4, room: 'work_zone' },
    { type: 'printer', x: 7, y: 1, room: 'work_zone' },

    // Meeting Room
    { type: 'big_table', x: 13, y: 3, room: 'meeting' },
    { type: 'chair', x: 12, y: 3, room: 'meeting', facing: 'right' },
    { type: 'chair', x: 15, y: 3, room: 'meeting', facing: 'left' },
    { type: 'chair', x: 13, y: 2, room: 'meeting', facing: 'down' },
    { type: 'chair', x: 14, y: 2, room: 'meeting', facing: 'down' },
    { type: 'chair', x: 13, y: 5, room: 'meeting', facing: 'up' },
    { type: 'chair', x: 14, y: 5, room: 'meeting', facing: 'up' },
    { type: 'whiteboard', x: 16, y: 2, room: 'meeting' },
    { type: 'clock', x: 11, y: 1, room: 'meeting' },

    // Kitchen
    { type: 'fridge', x: 1, y: 9, room: 'kitchen' },
    { type: 'coffee', x: 3, y: 9, room: 'kitchen' },
    { type: 'table', x: 2, y: 12, room: 'kitchen' },
    { type: 'chair', x: 2, y: 11, room: 'kitchen', facing: 'down' },
    { type: 'chair', x: 2, y: 13, room: 'kitchen', facing: 'up' },
    { type: 'chair', x: 1, y: 12, room: 'kitchen', facing: 'right' },
    { type: 'chair', x: 3, y: 12, room: 'kitchen', facing: 'left' },
    { type: 'plant', x: 5, y: 13, room: 'kitchen' },
    { type: 'trash', x: 5, y: 9, room: 'kitchen' },

    // Game Room
    { type: 'couch', x: 10, y: 10, room: 'game_room' },
    { type: 'tv', x: 13, y: 10, room: 'game_room' },
    { type: 'plant', x: 9, y: 13, room: 'game_room' },
    { type: 'rug', x: 11, y: 12, room: 'game_room' },
    { type: 'poster', x: 9, y: 9, room: 'game_room' },

    // CEO Office
    { type: 'big_desk', x: 19, y: 7, room: 'boss_office' },
    { type: 'boss_chair', x: 19, y: 8, room: 'boss_office' },
    { type: 'bookshelf', x: 17, y: 5, room: 'boss_office' },
    { type: 'bookshelf', x: 18, y: 5, room: 'boss_office' },
    { type: 'plant', x: 22, y: 12, room: 'boss_office' },
    { type: 'lamp', x: 21, y: 7, room: 'boss_office' },
    { type: 'window', x: 22, y: 6, room: 'boss_office' },
    { type: 'painting', x: 20, y: 5, room: 'boss_office' },
];

// Agent shirt colors
export const AGENT_COLORS = {
    main: COLORS.shirtMain,
    coder: COLORS.shirtCoder,
    researcher: COLORS.shirtResearcher,
    analyst: COLORS.shirtAnalyst,
};

// State colors for status indicators
export const STATE_COLORS = {
    running: '#4ade80',
    idle: '#ffffff',
    waiting: '#facc15',
    error: '#ef4444',
    meeting: '#60a5fa',
};