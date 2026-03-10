// src/lib/canvas-layout.ts
import * as crypto from "crypto";
var CANVAS_COLORS = {
  RED: "1",
  // Critical, blocked
  ORANGE: "2",
  // High priority
  YELLOW: "3",
  // Medium priority
  GREEN: "4",
  // Done, success
  CYAN: "5",
  // Stats
  PURPLE: "6"
  // Knowledge graph
};
var LAYOUT = {
  LEFT_COLUMN_X: 0,
  LEFT_COLUMN_WIDTH: 500,
  RIGHT_COLUMN_X: 550,
  RIGHT_COLUMN_WIDTH: 450,
  GROUP_PADDING: 20,
  NODE_SPACING: 15,
  GROUP_SPACING: 50,
  DEFAULT_NODE_WIDTH: 280,
  DEFAULT_NODE_HEIGHT: 80,
  FILE_NODE_HEIGHT: 60,
  SMALL_NODE_HEIGHT: 50,
  GROUP_HEADER_HEIGHT: 40
};
function generateId() {
  return crypto.randomBytes(8).toString("hex");
}
function createTextNode(x, y, width, height, text, color) {
  const node = {
    id: generateId(),
    type: "text",
    x,
    y,
    width,
    height,
    text
  };
  if (color) node.color = color;
  return node;
}
function createFileNode(x, y, width, height, file, color) {
  const node = {
    id: generateId(),
    type: "file",
    x,
    y,
    width,
    height,
    file
  };
  if (color) node.color = color;
  return node;
}
function createGroupNode(x, y, width, height, label, color) {
  const node = {
    id: generateId(),
    type: "group",
    x,
    y,
    width,
    height,
    label
  };
  if (color) node.color = color;
  return node;
}
function createEdge(fromNode, fromSide, toNode, toSide, label, color) {
  const edge = {
    id: generateId(),
    fromNode,
    fromSide,
    toNode,
    toSide
  };
  if (label) edge.label = label;
  if (color) edge.color = color;
  return edge;
}
function stackNodesVertically(nodes, startX, startY, spacing = LAYOUT.NODE_SPACING) {
  let currentY = startY;
  const positionedNodes = [];
  for (const node of nodes) {
    positionedNodes.push({
      ...node,
      x: startX,
      y: currentY
    });
    currentY += node.height + spacing;
  }
  return {
    nodes: positionedNodes,
    totalHeight: currentY - startY - spacing
  };
}
function createGroupWithNodes(groupX, groupY, groupWidth, label, childNodes, color) {
  const padding = LAYOUT.GROUP_PADDING;
  const headerHeight = LAYOUT.GROUP_HEADER_HEIGHT;
  const stacked = stackNodesVertically(
    childNodes,
    groupX + padding,
    groupY + headerHeight + padding
  );
  const groupHeight = headerHeight + padding * 2 + stacked.totalHeight + LAYOUT.NODE_SPACING;
  const group = createGroupNode(groupX, groupY, groupWidth, groupHeight, label, color);
  return {
    group,
    nodes: stacked.nodes
  };
}
function getPriorityColor(priority) {
  switch (priority) {
    case "critical":
      return CANVAS_COLORS.RED;
    case "high":
      return CANVAS_COLORS.ORANGE;
    case "medium":
      return CANVAS_COLORS.YELLOW;
    default:
      return void 0;
  }
}
function truncateText(text, maxChars) {
  if (text.length <= maxChars) return text;
  return text.slice(0, maxChars - 3) + "...";
}
function formatCanvasText(lines) {
  return lines.join("\n");
}
function calculateColumnHeight(groups) {
  let height = 0;
  for (let i = 0; i < groups.length; i++) {
    height += groups[i].group.height;
    if (i < groups.length - 1) {
      height += LAYOUT.GROUP_SPACING;
    }
  }
  return height;
}
function positionGroupsVertically(groups, startY = 0) {
  let currentY = startY;
  const positioned = [];
  for (const { group, nodes } of groups) {
    const yOffset = currentY - group.y;
    positioned.push({
      group: { ...group, y: currentY },
      nodes: nodes.map((n) => ({ ...n, y: n.y + yOffset }))
    });
    currentY += group.height + LAYOUT.GROUP_SPACING;
  }
  return positioned;
}
function flattenGroups(groups) {
  const nodes = [];
  for (const { group, nodes: childNodes } of groups) {
    nodes.push(group);
    nodes.push(...childNodes);
  }
  return nodes;
}

export {
  CANVAS_COLORS,
  LAYOUT,
  generateId,
  createTextNode,
  createFileNode,
  createGroupNode,
  createEdge,
  stackNodesVertically,
  createGroupWithNodes,
  getPriorityColor,
  truncateText,
  formatCanvasText,
  calculateColumnHeight,
  positionGroupsVertically,
  flattenGroups
};
