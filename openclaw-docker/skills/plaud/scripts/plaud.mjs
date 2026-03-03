// Native fetch is used in Node.js 18+
import fs from 'fs';
import path from 'path';

const TOKEN = process.env.PLAUD_TOKEN;
const DOMAIN = process.env.PLAUD_API_DOMAIN || 'https://api-euc1.plaud.ai';

if (!TOKEN) {
    console.error('Error: PLAUD_TOKEN is not set.');
    process.exit(1);
}

const headers = {
    'Authorization': `Bearer ${TOKEN}`,
    'Content-Type': 'application/json'
};

async function listFiles() {
    const response = await fetch(`${DOMAIN}/file/simple/web`, { headers });
    const data = await response.json();
    if (!data.data_file_list && data.code !== 0) {
        console.error('Error listing files:', data.msg || 'Unknown error');
        process.exit(1);
    }

    console.log('| ID | Title | Created At |');
    console.log('|---|---|---|');
    const files = data.data_file_list || [];
    files.forEach(file => {
        console.log(`| ${file.id} | ${file.filename} | ${new Date(file.edit_time * 1000).toLocaleString()} |`);
    });
}

async function getSummary(fileId) {
    const response = await fetch(`${DOMAIN}/file/detail/${fileId}`, { headers });
    const data = await response.json();
    if (!data.data && data.code !== 0) {
        console.error('Error getting summary:', data.msg || 'Unknown error');
        process.exit(1);
    }

    const file = data.data;
    console.log(`# ${file.file_name}`);
    console.log(`\n**Created At:** ${new Date(file.start_time).toLocaleString()}`);

    if (file.content_list && file.content_list.length > 0) {
        console.log('\n## Content Links\n');
        file.content_list.forEach(content => {
            console.log(`- [${content.data_title}](${content.data_link})`);
        });
    }
}

async function downloadFile(fileId, outputPath) {
    // Step 1: Get download URL from Plaud API
    const response = await fetch(`${DOMAIN}/file/download/${fileId}`, { headers });
    const data = await response.json();

    // Check for API errors
    if (data.code !== 0) {
        console.error('Error getting download URL:', data.msg || 'Unknown error');
        process.exit(1);
    }

    const downloadUrl = data.data?.download_url;
    if (!downloadUrl) {
        console.error('Error: No download_url in response');
        process.exit(1);
    }

    console.log(`Download URL obtained: ${downloadUrl.substring(0, 60)}...`);

    // Step 2: Download actual file from S3 pre-signed URL
    console.log(`Downloading file to: ${outputPath}`);
    const fileResponse = await fetch(downloadUrl);

    if (!fileResponse.ok) {
        console.error(`Error downloading file: HTTP ${fileResponse.status}`);
        process.exit(1);
    }

    // Get binary data and save to file
    const arrayBuffer = await fileResponse.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);
    fs.writeFileSync(outputPath, buffer);

    const fileSizeMB = (buffer.length / (1024 * 1024)).toFixed(2);
    console.log(`✅ File downloaded successfully: ${outputPath} (${fileSizeMB} MB)`);
}

const command = process.argv[2];
const arg = process.argv[3];

switch (command) {
    case 'list':
        listFiles();
        break;
    case 'summary':
        if (!arg) {
            console.error('Usage: plaud.mjs summary <FILE_ID>');
            process.exit(1);
        }
        getSummary(arg);
        break;
    case 'download':
        if (!arg) {
            console.error('Usage: plaud.mjs download <FILE_ID> [OUTPUT_PATH]');
            process.exit(1);
        }
        const outputPath = process.argv[4] || 'audio.mp3';
        downloadFile(arg, outputPath);
        break;
    default:
        console.log('Usage: node plaud.mjs [list|summary|download] [ID] [OUTPUT_PATH]');
        console.log('');
        console.log('Commands:');
        console.log('  list                           List all recordings');
        console.log('  summary <FILE_ID>              Get transcript and summary');
        console.log('  download <FILE_ID> [output]    Download audio file (default: audio.mp3)');
}
