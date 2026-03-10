import { ProjectStatus, Project } from '../lib/project-utils.js';
import '../lib/task-utils.js';

/**
 * Project command for ClawVault
 * Manages project add/update/archive/list/show/tasks/board operations
 */

interface ProjectAddOptions {
    status?: ProjectStatus;
    owner?: string;
    team?: string[];
    client?: string;
    tags?: string[];
    description?: string;
    deadline?: string;
    repo?: string;
    url?: string;
    content?: string;
}
interface ProjectUpdateOptions {
    status?: ProjectStatus;
    owner?: string | null;
    team?: string[] | null;
    client?: string | null;
    tags?: string[] | null;
    description?: string | null;
    deadline?: string | null;
    repo?: string | null;
    url?: string | null;
}
interface ProjectArchiveOptions {
    reason?: string;
}
interface ProjectListOptions {
    status?: ProjectStatus;
    owner?: string;
    client?: string;
    tag?: string;
    json?: boolean;
}
interface ProjectShowOptions {
    json?: boolean;
}
interface ProjectTasksOptions {
    json?: boolean;
}
type ProjectBoardGroupBy = 'status' | 'owner' | 'client';
interface ProjectBoardOptions {
    output?: string;
    groupBy?: ProjectBoardGroupBy | string;
    now?: Date;
}
interface ProjectBoardLane {
    name: string;
    cards: string[];
}
interface ProjectBoardResult {
    outputPath: string;
    groupBy: ProjectBoardGroupBy;
    markdown: string;
    lanes: ProjectBoardLane[];
    projectCount: number;
}
declare function buildProjectBoardLanes(projects: Project[], groupBy: ProjectBoardGroupBy): ProjectBoardLane[];
declare function generateProjectBoardMarkdown(projects: Project[], options?: {
    groupBy?: ProjectBoardGroupBy | string;
    now?: Date;
}): string;
declare function syncProjectBoard(vaultPath: string, options?: ProjectBoardOptions): ProjectBoardResult;
declare function projectAdd(vaultPath: string, title: string, options?: ProjectAddOptions): Project;
declare function projectUpdate(vaultPath: string, slug: string, options: ProjectUpdateOptions): Project;
declare function projectArchive(vaultPath: string, slug: string, options?: ProjectArchiveOptions): Project;
declare function projectList(vaultPath: string, options?: ProjectListOptions): Project[];
declare function formatProjectList(projects: Project[]): string;
declare function formatProjectDetails(vaultPath: string, project: Project, options?: {
    activityLimit?: number;
}): string;
declare function projectCommand(vaultPath: string, action: 'add' | 'update' | 'archive' | 'list' | 'show' | 'tasks' | 'board', args: {
    title?: string;
    slug?: string;
    options?: ProjectAddOptions & ProjectUpdateOptions & ProjectArchiveOptions & ProjectListOptions & ProjectShowOptions & ProjectTasksOptions & ProjectBoardOptions;
}): Promise<void>;

export { type ProjectAddOptions, type ProjectArchiveOptions, type ProjectBoardGroupBy, type ProjectBoardLane, type ProjectBoardOptions, type ProjectBoardResult, type ProjectListOptions, type ProjectShowOptions, type ProjectTasksOptions, type ProjectUpdateOptions, buildProjectBoardLanes, formatProjectDetails, formatProjectList, generateProjectBoardMarkdown, projectAdd, projectArchive, projectCommand, projectList, projectUpdate, syncProjectBoard };
