require('dotenv').config();
const { Client, GatewayIntentBits } = require('discord.js');
const axios = require('axios');

const DISCORD_BOT_TOKEN = process.env.DISCORD_BOT_TOKEN;
const FASTAPI_URL = process.env.FASTAPI_URL || "http://localhost:8000/webhook";

if (!DISCORD_BOT_TOKEN) {
  console.error("❌ ERROR: DISCORD_BOT_TOKEN is not set in .env!");
  process.exit(1);
}

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ]
});

client.on('ready', () => {
  console.log(`✅ Switch Discord Bridge connected as: ${client.user.tag}`);
  console.log(`📡 Forwarding PR/Code reviews to: ${FASTAPI_URL}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  if (message.content.includes("github.com") || message.content.includes("```")) {
    const statusMsg = await message.reply("🔍 Reviewing PR / Code snippet with Gemini 1.5 Flash...");
    try {
      const response = await axios.post(FASTAPI_URL, {
        content: message.content,
        author: message.author.username,
        chat_id: message.channel.id
      });

      const replyText = response.data.response || "⚠️ No review generated.";

      // Discord has a 2000 character limit per message
      if (replyText.length > 2000) {
        const chunks = replyText.match(/[\s\S]{1,1900}/g) || [replyText];
        await statusMsg.edit(chunks[0]);
        for (let i = 1; i < chunks.length; i++) {
          await message.channel.send(chunks[i]);
        }
      } else {
        await statusMsg.edit(replyText);
      }
    } catch (err) {
      console.error("FastAPI connection error:", err.message);
      await statusMsg.edit("⚠️ Error: Could not connect to Python FastAPI Reviewer (Port 8000). Make sure `python main.py` is running!");
    }
  }
});

client.login(DISCORD_BOT_TOKEN);
