import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// Simplistic migration script from LanceDB to Viking
// It assumes the lance DB is at ~/.openclaw/memory/lancedb
// We dynamically import lancedb to read the data.

const LANCEDB_PATH = path.join(os.homedir(), '.openclaw', 'memory', 'lancedb');
const VIKING_BRIDGE_URL = 'http://localhost:8100/memory/store';

async function migrate() {
    console.log(`Starting migration from LanceDB (${LANCEDB_PATH}) to Viking...`);

    if (!fs.existsSync(LANCEDB_PATH)) {
        console.log('No LanceDB found at ' + LANCEDB_PATH + '. Nothing to migrate.');
        return;
    }

    try {
        const lancedb = await import('@lancedb/lancedb');
        const db = await lancedb.connect(LANCEDB_PATH);
        
        const tables = await db.tableNames();
        if (!tables.includes('memories')) {
             console.log('No "memories" table found in LanceDB. Nothing to migrate.');
             return;
        }

        const table = await db.openTable('memories');
        // Fetch all records. Note: limit(10000) is arbitrary, adjust if db is huge.
        const records = await table.query().limit(10000).toArray();
        
        console.log(`Found ${records.length} memories in LanceDB. Migrating to Viking...`);

        let successCount = 0;
        let errorCount = 0;

        for (const record of records) {
            const text = record.text as string;
            if (!text) continue;

            try {
                const res = await fetch(VIKING_BRIDGE_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text })
                });

                if (res.ok) {
                    successCount++;
                } else {
                    console.error(`Failed to migrate record: ${text.substring(0, 50)}... status: ${res.status}`);
                    errorCount++;
                }
            } catch (err) {
                 console.error(`Error migrating record: ${text.substring(0, 50)}... error: ${String(err)}`);
                 errorCount++;
            }
        }

        console.log(`Migration complete! Successfully migrated: ${successCount}, Errors: ${errorCount}`);

    } catch (err) {
        console.error('Migration failed with critical error:', err);
    }
}

migrate();
