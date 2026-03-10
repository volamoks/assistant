import { Task } from './task-utils.js';

/**
 * Project utilities for ClawVault project tracking
 * Handles project definition and activity file read/write/query operations
 */

type ProjectStatus = 'active' | 'paused' | 'completed' | 'archived';
interface ProjectFrontmatter {
    type: 'project';
    status: ProjectStatus;
    created: string;
    updated: string;
    owner?: string;
    team?: string[];
    client?: string;
    tags?: string[];
    description?: string;
    started?: string;
    deadline?: string;
    repo?: string;
    url?: string;
    completed?: string;
    reason?: string;
}
interface Project {
    slug: string;
    title: string;
    content: string;
    frontmatter: ProjectFrontmatter;
}
interface ProjectFilterOptions {
    status?: ProjectStatus;
    owner?: string;
    client?: string;
    tag?: string;
}
interface CreateProjectOptions {
    status?: ProjectStatus;
    owner?: string;
    team?: string[];
    client?: string;
    tags?: string[];
    description?: string;
    started?: string;
    deadline?: string;
    repo?: string;
    url?: string;
    completed?: string;
    reason?: string;
    content?: string;
}
interface UpdateProjectOptions {
    status?: ProjectStatus;
    owner?: string | null;
    team?: string[] | null;
    client?: string | null;
    tags?: string[] | null;
    description?: string | null;
    started?: string | null;
    deadline?: string | null;
    repo?: string | null;
    url?: string | null;
    completed?: string | null;
    reason?: string | null;
}
/**
 * List all project definition files in the vault.
 * Includes only root-level projects/*.md files with type: project frontmatter.
 */
declare function listProjects(vaultPath: string, filters?: ProjectFilterOptions): Project[];
/**
 * Read a project definition file from projects/{slug}.md
 */
declare function readProject(vaultPath: string, slug: string): Project | null;
/**
 * Create a new project definition at projects/{slug}.md
 */
declare function createProject(vaultPath: string, title: string, options?: CreateProjectOptions): Project;
/**
 * Update an existing project's frontmatter
 */
declare function updateProject(vaultPath: string, slug: string, updates: UpdateProjectOptions): Project;
/**
 * Archive a project with optional reason and completion date
 */
declare function archiveProject(vaultPath: string, slug: string, reason?: string): Project;
/**
 * List tasks linked to a project by task.frontmatter.project === project slug
 */
declare function getProjectTasks(vaultPath: string, slug: string): Task[];
/**
 * List files in projects/{slug}/ sorted by date (newest first)
 */
declare function getProjectActivity(vaultPath: string, slug: string): string[];

export { type CreateProjectOptions, type Project, type ProjectFilterOptions, type ProjectFrontmatter, type ProjectStatus, type UpdateProjectOptions, archiveProject, createProject, getProjectActivity, getProjectTasks, listProjects, readProject, updateProject };
