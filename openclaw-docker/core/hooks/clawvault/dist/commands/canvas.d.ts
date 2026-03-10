import { Canvas } from '../lib/canvas-layout.js';

interface CanvasOptions {
    output?: string;
}
/**
 * Generate the vault status canvas.
 */
declare function generateCanvas(vaultPath: string): Canvas;
/**
 * Canvas command handler for CLI.
 */
declare function canvasCommand(vaultPath: string, options?: CanvasOptions): Promise<void>;

export { type CanvasOptions, canvasCommand, generateCanvas };
