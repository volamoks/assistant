// src/types.ts
var DEFAULT_CATEGORIES = [
  "rules",
  "preferences",
  "decisions",
  "patterns",
  "people",
  "projects",
  "goals",
  "transcripts",
  "inbox",
  "templates",
  "lessons",
  "agents",
  "commitments",
  "handoffs",
  "research",
  "tasks",
  "backlog"
];
var MEMORY_TYPES = [
  "fact",
  "feeling",
  "decision",
  "lesson",
  "commitment",
  "preference",
  "relationship",
  "project"
];
var TYPE_TO_CATEGORY = {
  fact: "facts",
  feeling: "feelings",
  decision: "decisions",
  lesson: "lessons",
  commitment: "commitments",
  preference: "preferences",
  relationship: "people",
  project: "projects"
};
var DEFAULT_CONFIG = {
  categories: DEFAULT_CATEGORIES
};

export {
  DEFAULT_CATEGORIES,
  MEMORY_TYPES,
  TYPE_TO_CATEGORY,
  DEFAULT_CONFIG
};
