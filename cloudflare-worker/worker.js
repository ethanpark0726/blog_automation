/**
 * Cloudflare Worker: Telegram → GitHub Actions Bridge
 *
 * Role: Receives Telegram webhook POSTs and triggers GitHub Actions workflow_dispatch.
 *
 * Environment Variables (Cloudflare Dashboard > Worker > Settings > Variables):
 *   - TELEGRAM_BOT_TOKEN : Telegram bot token issued by BotFather
 *   - GITHUB_TOKEN       : GitHub Personal Access Token (repo scope)
 *   - GITHUB_REPO        : Repository name in "username/repo-name" format
 *   - ALLOWED_CHAT_ID    : Allowed Telegram chat ID (for security, string)
 */

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Cloudflare Worker also handles GET ping requests
  if (request.method === "GET") {
    return new Response(
      JSON.stringify({ status: "ok", message: "Telegram-GitHub Bridge is running ✅" }),
      { status: 200, headers: { "Content-Type": "application/json" } }
    );
  }

  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405 });
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return new Response("Bad Request: Invalid JSON", { status: 400 });
  }

  // ── Message Parsing ──────────────────────────────────────────
  const message = body?.message || body?.edited_message;
  if (!message) {
    // Ignore other Telegram update types (e.g., inline query)
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  const chatId = String(message?.chat?.id);
  const text = message?.text;

  // ── Security: Only process allowed chat IDs ──────────────────
  if (!ALLOWED_CHAT_ID || ALLOWED_CHAT_ID.trim() === "") {
    console.error("Security Warning: ALLOWED_CHAT_ID is not configured. Requests are blocked by default.");
    return new Response("Forbidden: Worker environment not secure (missing ALLOWED_CHAT_ID)", { status: 403 });
  }

  if (chatId !== String(ALLOWED_CHAT_ID).trim()) {
    console.log(`Blocked request from unauthorized chat_id: ${chatId}`);
    // Return 200 OK to Telegram (to prevent infinite retries)
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── Command Filtering ───────────────────────────────────────
  if (!text || text.startsWith("/")) {
    if (text === "/start") {
      await sendTelegramMessage(
        chatId,
        "👋 Hello! I'm the Blog Automation Bot.\n\n✍️ Please enter a topic or question you'd like to turn into a blog post!\n\n Examples:\n• `What is Kubernetes?`\n• `Explain quantum computers to a child`"
      );
    } else if (text === "/status") {
      await sendTelegramMessage(chatId, "✅ Bot is running normally!");
    }
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── GitHub Actions Trigger ──────────────────────────────────
  console.log(`Triggering GitHub Actions for query: "${text}"`);

  try {
    await sendTelegramMessage(
      chatId,
      `⚙️ Request received!\n\n📝 Topic: "${text}"\n\n✍️ The Writer and Editor agents are starting work. Please wait a moment! (usually takes 2–3 minutes)`
    );

    const ghResponse = await triggerGitHubAction(text, chatId);

    if (ghResponse.ok) {
      // GitHub Actions triggered successfully (actual completion notification sent by Actions workflow)
      console.log("GitHub Actions triggered successfully");
    } else {
      const errBody = await ghResponse.text();
      console.error(`GitHub API Error: ${ghResponse.status} - ${errBody}`);
      await sendTelegramMessage(
        chatId,
        `❌ Failed to trigger GitHub Actions.\nError code: ${ghResponse.status}\nPlease contact the administrator.`
      );
    }
  } catch (err) {
    console.error("Error triggering GitHub Actions:", err);
    await sendTelegramMessage(chatId, `❌ An internal error occurred: ${err.message}`);
  }

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Trigger GitHub Actions workflow_dispatch
 */
async function triggerGitHubAction(queryInput, chatId) {
  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/telegram_trigger.yml/dispatches`;

  return fetch(url, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github.v3+json",
      "Content-Type": "application/json",
      "User-Agent": "TelegramBlogBot/1.0",
    },
    body: JSON.stringify({
      ref: "main",
      inputs: {
        query_input: queryInput,
        chat_id: String(chatId),
      },
    }),
  });
}

/**
 * Send a Telegram message
 */
async function sendTelegramMessage(chatId, text) {
  const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      chat_id: chatId,
      text: text,
      parse_mode: "Markdown",
    }),
  });
  return response;
}
