#!/usr/bin/env node
/**
 * Performance Comparison: Composio SDK vs Gemini CLI with MCP
 *
 * This script compares the latency of two approaches:
 * 1. Current: Node.js SDK calling Composio API directly
 * 2. New: Gemini CLI with Composio MCP server
 *
 * Test operations:
 * - List Gmail messages (read operation)
 * - Send test email (write operation - optional)
 */

import { execSync, spawn } from "child_process";
import { readFileSync, existsSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Load environment from openclaw-docker/.env if exists
const envPath = join(__dirname, "../../openclaw-docker/.env");
if (existsSync(envPath)) {
    const envContent = readFileSync(envPath, "utf8");
    envContent.split("\n").forEach((line) => {
        const match = line.match(/^([^#=]+)=(.*)$/);
        if (match && !process.env[match[1]]) {
            process.env[match[1]] = match[2];
        }
    });
}

// Configuration
const TEST_CONFIG = {
    iterations: 3, // Number of test runs for averaging
    testEmailRecipient: "s7abror@gmail.com",
    skipWriteTests: true, // Set to false to test email sending
};

// Colors for output
const colors = {
    reset: "\x1b[0m",
    bright: "\x1b[1m",
    red: "\x1b[31m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    blue: "\x1b[34m",
    cyan: "\x1b[36m",
};

const log = {
    info: (msg) => console.log(`${colors.blue}ℹ ${msg}${colors.reset}`),
    success: (msg) => console.log(`${colors.green}✓ ${msg}${colors.reset}`),
    error: (msg) => console.log(`${colors.red}✗ ${msg}${colors.reset}`),
    warn: (msg) => console.log(`${colors.yellow}⚠ ${msg}${colors.reset}`),
    header: (msg) => console.log(`\n${colors.bright}${colors.cyan}${msg}${colors.reset}`),
    result: (label, value) => console.log(`  ${label.padEnd(30)} ${colors.cyan}${value}${colors.reset}`),
};

// Performance timer class
class PerformanceTimer {
    constructor() {
        this.times = {};
    }

    start(label) {
        this.times[label] = { start: process.hrtime.bigint() };
    }

    end(label) {
        if (!this.times[label]) return 0;
        const end = process.hrtime.bigint();
        const duration = Number(end - this.times[label].start) / 1_000_000; // Convert to ms
        this.times[label].duration = duration;
        return duration;
    }

    getDuration(label) {
        return this.times[label]?.duration || 0;
    }
}

// Check prerequisites
async function checkPrerequisites() {
    log.header("=== Checking Prerequisites ===");

    const checks = {
        composioApiKey: !!process.env.COMPOSIO_API_KEY,
        geminiInstalled: false,
        geminiConfig: false,
        composioMcpConfigured: false,
    };

    // Check Composio API key
    if (checks.composioApiKey) {
        log.success("COMPOSIO_API_KEY is set");
    } else {
        log.error("COMPOSIO_API_KEY not set!");
        log.info("Set it with: export COMPOSIO_API_KEY='your-api-key'");
    }

    // Check Gemini CLI
    try {
        execSync("which gemini", { stdio: "pipe" });
        checks.geminiInstalled = true;
        log.success("Gemini CLI is installed");
    } catch {
        log.error("Gemini CLI not found!");
        log.info("Install with: npm install -g @google/gemini-cli");
    }

    // Check Gemini config
    const geminiSettingsPath = join(process.env.HOME, ".gemini", "settings.json");
    if (existsSync(geminiSettingsPath)) {
        checks.geminiConfig = true;
        log.success("Gemini settings.json exists");

        try {
            const settings = JSON.parse(readFileSync(geminiSettingsPath, "utf8"));
            if (settings.mcp?.servers?.composio) {
                checks.composioMcpConfigured = true;
                log.success("Composio MCP server is configured in Gemini");
            } else {
                log.warn("Composio MCP not configured in Gemini settings");
                log.info("Run: ./setup-gemini-mcp.sh");
            }
        } catch (e) {
            log.error("Failed to parse Gemini settings.json");
        }
    } else {
        log.error("Gemini settings.json not found");
    }

    return checks;
}

// Method 1: Direct Composio SDK call
async function testDirectSDK(operation) {
    const timer = new PerformanceTimer();

    log.info(`Testing Direct SDK: ${operation}...`);
    timer.start("total");
    timer.start("init");

    try {
        // Dynamic import to measure init time
        const { Composio } = await import("@composio/core");
        timer.end("init");

        timer.start("execution");

        const composio = new Composio({
            apiKey: process.env.COMPOSIO_API_KEY,
        });

        let result;
        if (operation === "listEmails") {
            // Get connected account first
            const connectionsResponse = await composio.connectedAccounts.list();
            const connections = connectionsResponse.items || connectionsResponse.data || connectionsResponse;
            const gmailAccount = connections.find((c) =>
                c.appName?.toLowerCase().includes("gmail")
            );

            if (!gmailAccount) {
                throw new Error("No Gmail account connected to Composio");
            }

            // Execute action
            result = await composio.actions.execute({
                actionName: "GMAIL_FETCH_EMAILS",
                requestBody: {
                    connectedAccountId: gmailAccount.id,
                    maxResults: 5,
                },
            });
        } else if (operation === "sendEmail" && !TEST_CONFIG.skipWriteTests) {
            const connectionsResponse = await composio.connectedAccounts.list();
            const connections = connectionsResponse.items || connectionsResponse.data || connectionsResponse;
            const gmailAccount = connections.find((c) =>
                c.appName?.toLowerCase().includes("gmail")
            );

            result = await composio.actions.execute({
                actionName: "GMAIL_SEND_EMAIL",
                requestBody: {
                    connectedAccountId: gmailAccount.id,
                    recipient: TEST_CONFIG.testEmailRecipient,
                    subject: "MCP Performance Test",
                    body: "This is a test email from the performance comparison script.",
                },
            });
        }

        timer.end("execution");
        timer.end("total");

        return {
            success: true,
            initTime: timer.getDuration("init"),
            executionTime: timer.getDuration("execution"),
            totalTime: timer.getDuration("total"),
            result: operation === "listEmails" ? `Found ${result?.data?.length || 0} emails` : "Email sent",
        };
    } catch (error) {
        timer.end("execution");
        timer.end("total");

        return {
            success: false,
            initTime: timer.getDuration("init"),
            executionTime: timer.getDuration("execution"),
            totalTime: timer.getDuration("total"),
            error: error.message,
        };
    }
}

// Method 2: Gemini CLI with MCP
async function testGeminiMcp(operation) {
    const timer = new PerformanceTimer();

    log.info(`Testing Gemini MCP: ${operation}...`);
    timer.start("total");
    timer.start("init");

    try {
        // Gemini needs to initialize and connect to MCP server
        const prompt =
            operation === "listEmails"
                ? "List my 5 most recent Gmail messages. Return only the count and subject lines."
                : `Send an email to ${TEST_CONFIG.testEmailRecipient} with subject "MCP Test" and body "Testing Gemini MCP"`;

        timer.end("init");
        timer.start("execution");

        // Run Gemini with the prompt
        const geminiProcess = spawn("gemini", [prompt], {
            stdio: ["pipe", "pipe", "pipe"],
            env: { ...process.env },
        });

        let output = "";
        let errorOutput = "";

        geminiProcess.stdout.on("data", (data) => {
            output += data.toString();
        });

        geminiProcess.stderr.on("data", (data) => {
            errorOutput += data.toString();
        });

        const exitCode = await new Promise((resolve) => {
            geminiProcess.on("close", resolve);
            // Timeout after 60 seconds
            setTimeout(() => {
                geminiProcess.kill();
                resolve(-1);
            }, 60000);
        });

        timer.end("execution");
        timer.end("total");

        if (exitCode === -1) {
            return {
                success: false,
                initTime: timer.getDuration("init"),
                executionTime: timer.getDuration("execution"),
                totalTime: timer.getDuration("total"),
                error: "Timeout after 60 seconds",
            };
        }

        if (exitCode !== 0 && !output.includes("email") && !output.includes("message")) {
            return {
                success: false,
                initTime: timer.getDuration("init"),
                executionTime: timer.getDuration("execution"),
                totalTime: timer.getDuration("total"),
                error: errorOutput || `Exit code: ${exitCode}`,
            };
        }

        return {
            success: true,
            initTime: timer.getDuration("init"),
            executionTime: timer.getDuration("execution"),
            totalTime: timer.getDuration("total"),
            result: output.substring(0, 200) + "...",
        };
    } catch (error) {
        timer.end("execution");
        timer.end("total");

        return {
            success: false,
            initTime: timer.getDuration("init"),
            executionTime: timer.getDuration("execution"),
            totalTime: timer.getDuration("total"),
            error: error.message,
        };
    }
}

// Run comparison tests
async function runComparison() {
    log.header("=== Composio SDK vs Gemini MCP Performance Comparison ===");
    log.info(`Running ${TEST_CONFIG.iterations} iterations per test...`);

    const results = {
        directSDK: [],
        geminiMcp: [],
    };

    // Test 1: List Emails (Read Operation)
    log.header("--- Test: List Gmail Messages ---");

    for (let i = 0; i < TEST_CONFIG.iterations; i++) {
        log.info(`Iteration ${i + 1}/${TEST_CONFIG.iterations}`);

        // Direct SDK
        const sdkResult = await testDirectSDK("listEmails");
        results.directSDK.push(sdkResult);

        if (sdkResult.success) {
            log.success(`Direct SDK: ${sdkResult.totalTime.toFixed(2)}ms`);
        } else {
            log.error(`Direct SDK failed: ${sdkResult.error}`);
        }

        // Wait between tests
        await new Promise((r) => setTimeout(r, 1000));

        // Gemini MCP
        const mcpResult = await testGeminiMcp("listEmails");
        results.geminiMcp.push(mcpResult);

        if (mcpResult.success) {
            log.success(`Gemini MCP: ${mcpResult.totalTime.toFixed(2)}ms`);
        } else {
            log.error(`Gemini MCP failed: ${mcpResult.error}`);
        }

        // Wait between iterations
        if (i < TEST_CONFIG.iterations - 1) {
            await new Promise((r) => setTimeout(r, 2000));
        }
    }

    return results;
}

// Calculate and display statistics
function displayResults(results) {
    log.header("=== Performance Results ===");

    const calculateStats = (data, field) => {
        const values = data.filter((r) => r.success).map((r) => r[field]);
        if (values.length === 0) return null;

        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const min = Math.min(...values);
        const max = Math.max(...values);

        return { avg: avg.toFixed(2), min: min.toFixed(2), max: max.toFixed(2), count: values.length };
    };

    // Direct SDK Stats
    log.header("Direct Composio SDK:");
    const sdkTotal = calculateStats(results.directSDK, "totalTime");
    const sdkInit = calculateStats(results.directSDK, "initTime");
    const sdkExec = calculateStats(results.directSDK, "executionTime");

    if (sdkTotal) {
        log.result("Successful runs:", sdkTotal.count);
        log.result("Total time (avg):", `${sdkTotal.avg}ms`);
        log.result("Init time (avg):", `${sdkInit?.avg || 0}ms`);
        log.result("Execution time (avg):", `${sdkExec?.avg || 0}ms`);
        log.result("Range:", `${sdkTotal.min}ms - ${sdkTotal.max}ms`);
    } else {
        log.error("No successful runs");
    }

    // Gemini MCP Stats
    log.header("Gemini CLI with MCP:");
    const mcpTotal = calculateStats(results.geminiMcp, "totalTime");
    const mcpInit = calculateStats(results.geminiMcp, "initTime");
    const mcpExec = calculateStats(results.geminiMcp, "executionTime");

    if (mcpTotal) {
        log.result("Successful runs:", mcpTotal.count);
        log.result("Total time (avg):", `${mcpTotal.avg}ms`);
        log.result("Init time (avg):", `${mcpInit?.avg || 0}ms`);
        log.result("Execution time (avg):", `${mcpExec?.avg || 0}ms`);
        log.result("Range:", `${mcpTotal.min}ms - ${mcpTotal.max}ms`);
    } else {
        log.error("No successful runs");
    }

    // Comparison
    log.header("=== Comparison ===");
    if (sdkTotal && mcpTotal) {
        const diff = parseFloat(mcpTotal.avg) - parseFloat(sdkTotal.avg);
        const percent = ((diff / parseFloat(sdkTotal.avg)) * 100).toFixed(1);

        if (diff > 0) {
            log.warn(`Gemini MCP is ${diff.toFixed(2)}ms slower (${percent}% slower)`);
            log.info("Direct SDK is faster for this operation");
        } else {
            log.success(`Gemini MCP is ${Math.abs(diff).toFixed(2)}ms faster (${Math.abs(percent)}% faster)`);
            log.info("MCP approach is faster for this operation");
        }

        console.log("");
        console.log(`${colors.bright}Analysis:${colors.reset}`);
        console.log("  • SDK init time: Module loading + API client setup");
        console.log("  • MCP init time: Gemini CLI startup + MCP server connection");
        console.log("  • SDK execution: Direct HTTP API calls");
        console.log("  • MCP execution: LLM processing + tool calls");
    }

    // Recommendations
    log.header("=== Recommendations ===");
    if (sdkTotal && mcpTotal) {
        const sdkAvg = parseFloat(sdkTotal.avg);
        const mcpAvg = parseFloat(mcpTotal.avg);

        if (sdkAvg < mcpAvg * 0.5) {
            console.log("  Direct SDK is significantly faster for programmatic use.");
            console.log("  Use Gemini MCP for: Interactive CLI usage, complex multi-step tasks");
            console.log("  Use Direct SDK for: Automated scripts, low-latency operations");
        } else if (mcpAvg < sdkAvg * 0.5) {
            console.log("  Gemini MCP is significantly faster!");
            console.log("  Consider migrating to MCP for better performance.");
        } else {
            console.log("  Both approaches have similar performance.");
            console.log("  Choose based on use case: SDK for code, MCP for CLI interaction.");
        }
    }
}

// Main execution
async function main() {
    console.log(`${colors.bright}${colors.cyan}`);
    console.log("╔════════════════════════════════════════════════════════════╗");
    console.log("║  Composio SDK vs Gemini MCP Performance Comparison         ║");
    console.log("╚════════════════════════════════════════════════════════════╝");
    console.log(`${colors.reset}`);

    // Check prerequisites
    const checks = await checkPrerequisites();

    if (!checks.composioApiKey || !checks.geminiInstalled) {
        log.error("Missing prerequisites. Please fix the issues above.");
        process.exit(1);
    }

    if (!checks.composioMcpConfigured) {
        log.warn("Composio MCP not configured. Running SDK-only test.");
        log.info("Run ./setup-gemini-mcp.sh to enable MCP comparison.");
    }

    console.log("");
    log.info("Starting performance tests...");
    log.info("This may take a few minutes...");
    console.log("");

    try {
        const results = await runComparison();
        displayResults(results);

        // Save raw results to file
        const resultsPath = join(__dirname, "results.json");
        const resultsData = {
            timestamp: new Date().toISOString(),
            config: TEST_CONFIG,
            results: results,
        };
        require("fs").writeFileSync(resultsPath, JSON.stringify(resultsData, null, 2));
        log.info(`Raw results saved to: ${resultsPath}`);
    } catch (error) {
        log.error(`Test failed: ${error.message}`);
        console.error(error);
        process.exit(1);
    }
}

// Run main
main().catch((error) => {
    console.error("Fatal error:", error);
    process.exit(1);
});
