import fs from 'fs';
import path from 'path';
import fetch from 'node-fetch';
import FormData from 'form-data';

const UNSTRUCTURED_URL = 'http://unstructured-api:8000/general/v0/general';

/**
 * Skill: Document Intelligence
 * Extracts text and structure from various file formats.
 */
export async function run({ filePath }) {
    if (!filePath) {
        throw new Error("Missing filePath parameter.");
    }

    // Check if file exists
    if (!fs.existsSync(filePath)) {
        throw new Error(`File not found: ${filePath}`);
    }

    const stats = fs.statSync(filePath);
    if (stats.size > 50 * 1024 * 1024) { // 50MB limit
        throw new Error("File is too large (max 50MB).");
    }

    const form = new FormData();
    form.append('files', fs.createReadStream(filePath));
    form.append('strategy', 'fast'); // Use 'hi_res' for OCR if needed, but 'fast' is better for text-based PDFs
    form.append('output_format', 'text/markdown');

    console.log(`[DocumentIntelligence] Sending ${filePath} to Unstructured API...`);

    const response = await fetch(UNSTRUCTURED_URL, {
        method: 'POST',
        body: form,
        headers: form.getHeaders(),
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Unstructured API error: ${response.statusText} - ${errorText}`);
    }

    const elements = await response.json();
    
    // Convert Unstructured elements to a simple Markdown string
    const markdown = elements.map(el => {
        if (el.type === 'Title') return `## ${el.text}`;
        if (el.type === 'ListItem') return `- ${el.text}`;
        if (el.type === 'Table') return `
[Table]
${el.metadata.text_as_html || el.text}
`;
        return el.text;
    }).join('

');

    return {
        content: markdown,
        metadata: {
            filename: path.basename(filePath),
            elementCount: elements.length
        }
    };
}
