#!/usr/bin/env node
/**
 * bird — X/Twitter CLI через Sweetistics API
 * Usage: bird <command> [args]
 */

import { execSync } from 'child_process';

const API_KEY = process.env.SWEETISTICS_API_KEY;
const API_BASE = 'https://api.sweetistics.com/v1';

if (!API_KEY) {
  console.error('❌ SWEETISTICS_API_KEY not set. Get one at https://sweetistics.com');
  process.exit(1);
}

const command = process.argv[2];
const args = process.argv.slice(3);

async function apiCall(endpoint, params = {}) {
  const url = new URL(`${API_BASE}${endpoint}`);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  
  const cmd = `curl -sL "${url}" -H "Authorization: Bearer ${API_KEY}"`;
  return JSON.parse(execSync(cmd, { encoding: 'utf8' }));
}

async function main() {
  try {
    switch (command) {
      case 'whoami': {
        const user = await apiCall('/user/me');
        console.log(`✅ @${user.username} (${user.display_name || user.name})`);
        break;
      }
      
      case 'read': {
        const url = args[0];
        const id = url.match(/status\/(\d+)/)?.[1] || url;
        const tweet = await apiCall(`/tweets/${id}`);
        console.log(`@${tweet.author.username}: ${tweet.text}`);
        console.log(`❤️ ${tweet.likes} | 🔄 ${tweet.retweets} | 💬 ${tweet.replies}`);
        break;
      }
      
      case 'thread': {
        const url = args[0];
        const id = url.match(/status\/(\d+)/)?.[1] || url;
        const thread = await apiCall(`/tweets/${id}/thread`);
        thread.tweets.forEach((t, i) => {
          console.log(`\n[${i + 1}] @${t.author.username}:`);
          console.log(t.text);
        });
        break;
      }
      
      case 'search': {
        const query = args.find(a => !a.startsWith('-'));
        const count = parseInt(args.find(a => a === '-n')?.[1] || '5');
        const results = await apiCall('/search', { q: query, count });
        results.tweets.forEach((t, i) => {
          console.log(`\n${i + 1}. @${t.author.username} (${new Date(t.created_at).toLocaleDateString()})`);
          console.log(t.text.slice(0, 200));
          console.log(`URL: https://x.com/${t.author.username}/status/${t.id}`);
        });
        break;
      }
      
      case 'tweet': {
        const text = args.join(' ').replace(/^["']|["']$/g, '');
        console.log('⚠️ Posting requires confirmation. Use web interface or confirm first.');
        // POST not implemented in CLI - requires user confirmation
        break;
      }
      
      case 'check': {
        console.log('✅ Sweetistics API configured');
        console.log(`Key: ${API_KEY.slice(0, 8)}...`);
        break;
      }
      
      default:
        console.log('Usage: bird <command> [args]');
        console.log('Commands: whoami, read, thread, search, tweet, check');
        process.exit(1);
    }
  } catch (err) {
    console.error('❌ Error:', err.message);
    process.exit(1);
  }
}

main();
