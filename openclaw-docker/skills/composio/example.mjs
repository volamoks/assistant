/**
 * Composio Skill - Usage Examples
 * 
 * This file demonstrates how to use the Composio skill
 * for various integrations.
 */

import { run, getSkill } from "./index.mjs";

// Example 1: List all enabled services
async function exampleListServices() {
    console.log("=== Example 1: List Services ===");
    const services = await run({ mode: "list" });
    console.log(JSON.stringify(services, null, 2));
}

// Example 2: Get service details
async function exampleServiceDetails() {
    console.log("\n=== Example 2: Gmail Service Details ===");
    const details = await run({ mode: "details", service: "gmail" });
    console.log(JSON.stringify(details, null, 2));
}

// Example 3: Send email via Gmail
async function exampleSendEmail() {
    console.log("\n=== Example 3: Send Email ===");
    try {
        const result = await run({
            service: "gmail",
            action: "SEND_EMAIL",
            params: {
                to: ["s7abror@gmail.com"],
                subject: "Hello from Composio",
                body: "This is a test email sent via Composio MCP integration!"
            }
        });
        console.log("Email sent successfully:", result);
    } catch (error) {
        console.error("Failed to send email:", error.message);
    }
}

// Example 4: Query Claude with Gmail tools
async function exampleClaudeQuery() {
    console.log("\n=== Example 4: Claude Query with Gmail ===");
    try {
        const result = await run({
            mode: "query",
            prompt: "Send an email to s7abror@gmail.com with the subject 'Hello from Composio' and the body 'This is a test email!'",
            service: "gmail" // Only enable Gmail tools
        });
        console.log("Claude response:", result.result);
        console.log("Tool calls made:", result.toolCalls);
    } catch (error) {
        console.error("Claude query failed:", error.message);
    }
}

// Example 5: Batch operations
async function exampleBatch() {
    console.log("\n=== Example 5: Batch Operations ===");
    try {
        const results = await run({
            mode: "batch",
            actions: [
                {
                    service: "gmail",
                    action: "SEARCH_EMAILS",
                    params: { query: "from:github.com", max_results: 5 }
                },
                {
                    service: "gmail",
                    action: "SEARCH_EMAILS",
                    params: { query: "is:unread", max_results: 10 }
                }
            ]
        });
        console.log("Batch results:", JSON.stringify(results, null, 2));
    } catch (error) {
        console.error("Batch failed:", error.message);
    }
}

// Example 6: Direct skill usage with session management
async function exampleDirectUsage() {
    console.log("\n=== Example 6: Direct Skill Usage ===");

    const skill = await getSkill();

    // You can manually manage sessions
    const userId = "my-custom-user-123";
    const session = await skill.getSession(userId);
    console.log("Session created for user:", userId);

    // Execute action with specific user
    const result = await skill.run({
        service: "gmail",
        action: "SEARCH_EMAILS",
        params: { query: "is:unread", max_results: 5 },
        userId
    });

    console.log("Search result:", result);
}

// Example 7: Enable new service via config
// Just edit config.json and set "enabled": true for any service!
async function exampleEnableNewService() {
    console.log("\n=== Example 7: How to Enable New Service ===");
    console.log(`
To add a new service (e.g., Notion):

1. Go to config.json
2. Find "notion" service
3. Change "enabled": false → "enabled": true
4. Use it immediately:

   await run({
     service: "notion",
     action: "CREATE_PAGE",
     params: {
       parent: { database_id: "your-db-id" },
       properties: {
         title: { title: [{ text: { content: "New Page" } }] }
       }
     }
   });

No code changes needed! The skill automatically picks up new services from config.
`);
}

// Run all examples
async function main() {
    console.log("🚀 Composio Skill Examples\n");

    try {
        // Run examples based on command line args
        const examples = {
            list: exampleListServices,
            details: exampleServiceDetails,
            email: exampleSendEmail,
            query: exampleClaudeQuery,
            batch: exampleBatch,
            direct: exampleDirectUsage,
            enable: exampleEnableNewService,
            all: async () => {
                await exampleListServices();
                await exampleServiceDetails();
                await exampleEnableNewService();
                // Skip actual API calls in 'all' mode to avoid side effects
                console.log("\n(Skipping API calls in 'all' mode - run individually to test)");
            }
        };

        const arg = process.argv[2] || "all";
        const example = examples[arg];

        if (example) {
            await example();
        } else {
            console.log(`Unknown example: ${arg}`);
            console.log("Available: list, details, email, query, batch, direct, enable, all");
        }

    } catch (error) {
        console.error("\n❌ Error:", error.message);
        process.exit(1);
    }
}

main();
