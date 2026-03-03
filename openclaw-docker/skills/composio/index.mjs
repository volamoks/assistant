/**
 * Composio Universal Tools Skill
 * 
 * Flexible, configuration-driven integration with Composio MCP.
 * Add new services by editing config.json - no code changes needed!
 * 
 * Usage:
 *   await skill.run({ service: "gmail", action: "SEND_EMAIL", params: {...} })
 *   await skill.queryClaude({ prompt: "Send email...", service: "gmail" })
 */

import { Composio } from "@composio/core";
import { query } from "@anthropic-ai/claude-agent-sdk";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load configuration
let CONFIG = {};
try {
    const configPath = join(__dirname, "config.json");
    CONFIG = JSON.parse(readFileSync(configPath, "utf8"));
} catch (error) {
    console.warn("[Composio] Could not load config.json, using defaults:", error.message);
    CONFIG = { services: {}, claude: {}, defaults: {} };
}

// Environment configuration
const ENV = {
    COMPOSIO_API_KEY: process.env.COMPOSIO_API_KEY,
    COMPOSIO_BASE_URL: process.env.COMPOSIO_BASE_URL || "https://backend.composio.dev",
    CLAUDE_API_KEY: process.env.CLAUDE_API_KEY,
};

/**
 * Validates required parameters for an action
 */
function validateParams(serviceName, actionName, params, config) {
    const service = config.services?.[serviceName];
    if (!service) {
        throw new Error(`Service "${serviceName}" not found in config`);
    }

    const action = service.actions?.[actionName];
    if (!action) {
        throw new Error(`Action "${actionName}" not found for service "${serviceName}"`);
    }

    const required = action.requiredParams || [];
    const missing = required.filter(param => !(param in params));

    if (missing.length > 0) {
        throw new Error(`Missing required parameters for ${serviceName}.${actionName}: ${missing.join(", ")}`);
    }

    return true;
}

/**
 * Get enabled services list
 */
function getEnabledServices(config = CONFIG) {
    return Object.entries(config.services || {})
        .filter(([_, service]) => service.enabled)
        .map(([name, service]) => ({
            name,
            ...service
        }));
}

/**
 * Check if service is enabled
 */
function isServiceEnabled(serviceName, config = CONFIG) {
    return config.services?.[serviceName]?.enabled === true;
}

/**
 * Main Composio Skill Class
 */
class ComposioSkill {
    constructor() {
        this.composio = null;
        this.sessions = new Map(); // Cache sessions by userId
        this.config = CONFIG;
    }

    /**
     * Initialize Composio client
     */
    async init() {
        if (!ENV.COMPOSIO_API_KEY) {
            throw new Error("COMPOSIO_API_KEY environment variable is required");
        }

        this.composio = new Composio({
            apiKey: ENV.COMPOSIO_API_KEY,
            baseUrl: ENV.COMPOSIO_BASE_URL,
        });

        console.log("[Composio] Initialized successfully");
        return this;
    }

    /**
     * Get or create session for user
     */
    async getSession(externalUserId) {
        if (this.sessions.has(externalUserId)) {
            return this.sessions.get(externalUserId);
        }

        if (!this.composio) {
            await this.init();
        }

        const session = await this.composio.create(externalUserId);
        this.sessions.set(externalUserId, session);

        console.log(`[Composio] Created session for user: ${externalUserId}`);
        return session;
    }

    /**
     * Execute an action on a service
     * 
     * @param {Object} options
     * @param {string} options.service - Service name (e.g., "gmail")
     * @param {string} options.action - Action name (e.g., "SEND_EMAIL")
     * @param {Object} options.params - Action parameters
     * @param {string} options.userId - Optional user ID for session
     */
    async run({ service, action, params = {}, userId }) {
        // Validate
        if (!service || !action) {
            throw new Error("Both 'service' and 'action' are required");
        }

        if (!isServiceEnabled(service, this.config)) {
            throw new Error(`Service "${service}" is not enabled in config.json`);
        }

        validateParams(service, action, params, this.config);

        // Get session
        const externalUserId = userId || this.generateUserId();
        const session = await this.getSession(externalUserId);

        // Execute action via Composio
        try {
            console.log(`[Composio] Executing ${service}.${action}`, params);

            const result = await this.composio.executeAction({
                action: `${service.toUpperCase()}_${action}`,
                params,
                entityId: externalUserId,
            });

            console.log(`[Composio] Action ${service}.${action} completed successfully`);
            return {
                success: true,
                service,
                action,
                result,
            };
        } catch (error) {
            console.error(`[Composio] Action ${service}.${action} failed:`, error);
            throw error;
        }
    }

    /**
     * Query Claude with MCP tools enabled
     * 
     * @param {Object} options
     * @param {string} options.prompt - User prompt
     * @param {string} options.service - Service to enable (optional, enables all if not specified)
     * @param {string} options.userId - Optional user ID
     * @param {Object} options.options - Additional Claude options
     */
    async queryClaude({ prompt, service, userId, options = {} }) {
        if (!prompt) {
            throw new Error("Prompt is required");
        }

        // Get session
        const externalUserId = userId || this.generateUserId();
        const session = await this.getSession(externalUserId);

        // Build MCP servers config
        const mcpServers = {};

        if (service) {
            // Enable specific service
            if (!isServiceEnabled(service, this.config)) {
                throw new Error(`Service "${service}" is not enabled`);
            }
            mcpServers[service] = session.mcp;
        } else {
            // Enable all enabled services
            const enabledServices = getEnabledServices(this.config);
            for (const svc of enabledServices) {
                mcpServers[svc.name] = session.mcp;
            }
        }

        // Merge with Claude config
        const claudeConfig = this.config.claude || {};
        const queryOptions = {
            model: options.model || claudeConfig.model || "claude-sonnet-4-5-20250929",
            permissionMode: options.permissionMode || claudeConfig.permissionMode || "bypassPermissions",
            mcpServers,
            ...options,
        };

        console.log(`[Composio] Querying Claude with MCP servers:`, Object.keys(mcpServers));

        try {
            const stream = await query({
                prompt,
                options: queryOptions,
            });

            // Collect streaming response
            let result = "";
            let toolCalls = [];

            for await (const event of stream) {
                switch (event.type) {
                    case "result":
                        if (event.subtype === "success") {
                            result += event.result || "";
                        }
                        break;
                    case "tool_call":
                        toolCalls.push({
                            service: event.service,
                            action: event.action,
                            params: event.params,
                        });
                        console.log(`[Composio] Tool call: ${event.service}.${event.action}`);
                        break;
                    case "error":
                        console.error("[Composio] Claude error:", event.error);
                        throw new Error(event.error);
                }
            }

            return {
                success: true,
                result,
                toolCalls,
                prompt,
                servicesUsed: Object.keys(mcpServers),
            };
        } catch (error) {
            console.error("[Composio] Claude query failed:", error);
            throw error;
        }
    }

    /**
     * Batch execute multiple actions
     * 
     * @param {Array} actions - Array of { service, action, params, userId }
     */
    async batch(actions) {
        const results = [];

        for (const action of actions) {
            try {
                const result = await this.run(action);
                results.push({ success: true, ...result });
            } catch (error) {
                results.push({
                    success: false,
                    service: action.service,
                    action: action.action,
                    error: error.message
                });
            }
        }

        return results;
    }

    /**
     * List available services and actions
     */
    listServices() {
        const services = getEnabledServices(this.config);
        return services.map(s => ({
            name: s.name,
            description: s.description,
            actions: Object.keys(s.actions || {}),
        }));
    }

    /**
     * Get service details
     */
    getServiceDetails(serviceName) {
        const service = this.config.services?.[serviceName];
        if (!service) {
            return null;
        }

        return {
            name: serviceName,
            enabled: service.enabled,
            description: service.description,
            actions: service.actions,
        };
    }

    /**
     * Generate unique user ID
     */
    generateUserId() {
        const defaultTemplate = this.config.defaults?.externalUserId || "openclaw-user-{{timestamp}}";
        return defaultTemplate.replace("{{timestamp}}", Date.now().toString());
    }

    /**
     * Clear session cache
     */
    clearSessions() {
        this.sessions.clear();
        console.log("[Composio] Session cache cleared");
    }
}

// Singleton instance
let skillInstance = null;

/**
 * Get or create skill instance
 */
async function getSkill() {
    if (!skillInstance) {
        skillInstance = new ComposioSkill();
        await skillInstance.init();
    }
    return skillInstance;
}

/**
 * Main entry point for skill system
 * 
 * Supports multiple modes:
 * - run: Execute single action
 * - query: Query Claude with MCP
 * - batch: Execute multiple actions
 * - list: List available services
 */
export async function run(args) {
    const skill = await getSkill();

    // Mode-based routing
    const mode = args.mode || inferMode(args);

    switch (mode) {
        case "run":
            return skill.run({
                service: args.service,
                action: args.action,
                params: args.params || {},
                userId: args.userId,
            });

        case "query":
            return skill.queryClaude({
                prompt: args.prompt,
                service: args.service,
                userId: args.userId,
                options: args.options || {},
            });

        case "batch":
            return skill.batch(args.actions || []);

        case "list":
            return skill.listServices();

        case "details":
            return skill.getServiceDetails(args.service);

        default:
            throw new Error(`Unknown mode: ${mode}. Use: run, query, batch, list, details`);
    }
}

/**
 * Infer mode from args
 */
function inferMode(args) {
    if (args.prompt) return "query";
    if (args.actions) return "batch";
    if (args.service && args.action) return "run";
    if (args.service && !args.action) return "details";
    return "list";
}

// Convenience exports
export { ComposioSkill, getSkill, getEnabledServices, isServiceEnabled };

// Default export
export default { run, getSkill, ComposioSkill };

// Simple CLI for testing
if (process.argv[1] === fileURLToPath(import.meta.url)) {
    const args = process.argv.slice(2);

    if (args.length === 0) {
        console.log(`
Composio Skill CLI

Usage:
  node index.mjs list                    # List enabled services
  node index.mjs details <service>       # Get service details
  node index.mjs run <service> <action>  # Run action (params via stdin)
  node index.mjs query "<prompt>"        # Query Claude

Examples:
  node index.mjs list
  node index.mjs details gmail
  node index.mjs run gmail SEND_EMAIL '{"to":["test@example.com"],"subject":"Hi","body":"Hello"}'
  node index.mjs query "Send email to test@example.com saying hello"
`);
        process.exit(0);
    }

    const [command, ...rest] = args;

    (async () => {
        try {
            let result;

            switch (command) {
                case "list":
                    result = await run({ mode: "list" });
                    console.log(JSON.stringify(result, null, 2));
                    break;

                case "details":
                    result = await run({ mode: "details", service: rest[0] });
                    console.log(JSON.stringify(result, null, 2));
                    break;

                case "run": {
                    const [service, action, paramsJson] = rest;
                    const params = paramsJson ? JSON.parse(paramsJson) : {};
                    result = await run({ service, action, params });
                    console.log(JSON.stringify(result, null, 2));
                    break;
                }

                case "query":
                    result = await run({ mode: "query", prompt: rest.join(" ") });
                    console.log(JSON.stringify(result, null, 2));
                    break;

                default:
                    console.error(`Unknown command: ${command}`);
                    process.exit(1);
            }
        } catch (error) {
            console.error("Error:", error.message);
            process.exit(1);
        }
    })();
}
