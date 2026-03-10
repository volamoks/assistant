/**
 * Canvas layout utilities for ClawVault
 * Handles JSON Canvas generation with proper positioning and grouping
 */
interface CanvasNode {
    id: string;
    type: 'text' | 'file' | 'group';
    x: number;
    y: number;
    width: number;
    height: number;
    text?: string;
    file?: string;
    label?: string;
    color?: string;
}
interface CanvasEdge {
    id: string;
    fromNode: string;
    fromSide: 'top' | 'right' | 'bottom' | 'left';
    toNode: string;
    toSide: 'top' | 'right' | 'bottom' | 'left';
    label?: string;
    color?: string;
}
interface Canvas {
    nodes: CanvasNode[];
    edges: CanvasEdge[];
}
declare const CANVAS_COLORS: {
    readonly RED: "1";
    readonly ORANGE: "2";
    readonly YELLOW: "3";
    readonly GREEN: "4";
    readonly CYAN: "5";
    readonly PURPLE: "6";
};
declare const LAYOUT: {
    readonly LEFT_COLUMN_X: 0;
    readonly LEFT_COLUMN_WIDTH: 500;
    readonly RIGHT_COLUMN_X: 550;
    readonly RIGHT_COLUMN_WIDTH: 450;
    readonly GROUP_PADDING: 20;
    readonly NODE_SPACING: 15;
    readonly GROUP_SPACING: 50;
    readonly DEFAULT_NODE_WIDTH: 280;
    readonly DEFAULT_NODE_HEIGHT: 80;
    readonly FILE_NODE_HEIGHT: 60;
    readonly SMALL_NODE_HEIGHT: 50;
    readonly GROUP_HEADER_HEIGHT: 40;
};
/**
 * Generate a 16-character lowercase hex ID
 */
declare function generateId(): string;
/**
 * Create a text node
 */
declare function createTextNode(x: number, y: number, width: number, height: number, text: string, color?: string): CanvasNode;
/**
 * Create a file node
 */
declare function createFileNode(x: number, y: number, width: number, height: number, file: string, color?: string): CanvasNode;
/**
 * Create a group node
 */
declare function createGroupNode(x: number, y: number, width: number, height: number, label: string, color?: string): CanvasNode;
/**
 * Create an edge between nodes
 */
declare function createEdge(fromNode: string, fromSide: 'top' | 'right' | 'bottom' | 'left', toNode: string, toSide: 'top' | 'right' | 'bottom' | 'left', label?: string, color?: string): CanvasEdge;
/**
 * Layout helper for vertical stacking of nodes within a group
 */
interface StackedLayout {
    nodes: CanvasNode[];
    totalHeight: number;
}
declare function stackNodesVertically(nodes: CanvasNode[], startX: number, startY: number, spacing?: number): StackedLayout;
/**
 * Create a group with contained nodes
 * Returns the group node and positioned child nodes
 */
interface GroupWithNodes {
    group: CanvasNode;
    nodes: CanvasNode[];
}
declare function createGroupWithNodes(groupX: number, groupY: number, groupWidth: number, label: string, childNodes: CanvasNode[], color?: string): GroupWithNodes;
/**
 * Get priority color for a task
 */
declare function getPriorityColor(priority?: string): string | undefined;
/**
 * Truncate text to fit within a certain width (approximate)
 */
declare function truncateText(text: string, maxChars: number): string;
/**
 * Format markdown text for canvas node
 * Replaces newlines with \n for JSON Canvas spec
 */
declare function formatCanvasText(lines: string[]): string;
/**
 * Calculate the total height needed for a column of groups
 */
declare function calculateColumnHeight(groups: GroupWithNodes[]): number;
/**
 * Position groups vertically in a column
 */
declare function positionGroupsVertically(groups: GroupWithNodes[], startY?: number): GroupWithNodes[];
/**
 * Flatten groups and nodes into a single array
 */
declare function flattenGroups(groups: GroupWithNodes[]): CanvasNode[];

export { CANVAS_COLORS, type Canvas, type CanvasEdge, type CanvasNode, type GroupWithNodes, LAYOUT, type StackedLayout, calculateColumnHeight, createEdge, createFileNode, createGroupNode, createGroupWithNodes, createTextNode, flattenGroups, formatCanvasText, generateId, getPriorityColor, positionGroupsVertically, stackNodesVertically, truncateText };
