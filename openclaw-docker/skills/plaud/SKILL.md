# Plaud Skill

Sync and summarize recordings from Plaud Note devices using the Plaud.ai API.

## Commands

### `node skills/plaud/scripts/plaud.mjs list`
Lists recent recordings with their IDs, titles, and creation times.

### `node skills/plaud/scripts/plaud.mjs summary <FILE_ID>`
Retrieves the transcript and AI-generated summary for a specific recording.

### `node skills/plaud/scripts/plaud.mjs download <FILE_ID>`
Downloads the MP3 audio file for a recording.

## Configuration

Required environment variables:
- `PLAUD_TOKEN`: Your Plaud.ai authentication token.
- `PLAUD_API_DOMAIN`: The API endpoint for your region (e.g., `https://api-euc1.plaud.ai`).

## Usage Examples

- "List my recent Plaud recordings"
- "Summarize my last recording from Plaud"
- "Download the audio for Plaud recording <ID>"
