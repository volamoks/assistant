import { PlaudClient } from 'plaud-unofficial';

const [,, command, ...args] = process.argv;
const username = process.env.PLAUD_USERNAME;
const password = process.env.PLAUD_PASSWORD;

if (!username || !password) {
  console.error("Error: PLAUD_USERNAME and PLAUD_PASSWORD env vars required.");
  process.exit(1);
}

const client = new PlaudClient({ username, password });

async function main() {
  try {
    await client.login();
    
    switch (command) {
      case 'list':
        const files = await client.getFiles({ limit: 5 });
        console.log(JSON.stringify(files, null, 2));
        break;
      
      case 'summary':
        // Mock implementation assuming getFileSummary exists or similar
        // Adjust based on actual API
        const fileId = args[0];
        if (!fileId) throw new Error("File ID required");
        const summary = await client.getFileSummary(fileId); 
        console.log(JSON.stringify(summary, null, 2));
        break;

      default:
        console.log("Unknown command. Available: list, summary");
    }
  } catch (error) {
    console.error("Plaud Error:", error.message);
  }
}

main();
