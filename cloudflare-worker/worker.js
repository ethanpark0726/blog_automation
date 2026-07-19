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
  const trimmedText = typeof text === "string" ? text.trim() : "";
  const [rawCommand = "", ...commandArgs] = trimmedText.split(/\s+/);
  const command = rawCommand.split("@")[0].toLowerCase();

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
  if (command === "/help" || command === "/start") {
    await sendTelegramMessage(
      chatId,
      "🤖 *블로그 자동화 명령어*\n\n" +
        "• 새 글: 주제나 질문을 그대로 입력\n" +
        "• /status: 최근 생성·배포 상태 확인\n" +
        "• /reviews: pending 리뷰 노트 확인\n" +
        "• /revise: ready 리뷰 노트 기반으로 기존 글 보강\n" +
        "• /revise latest: 가장 최근 ready 리뷰 노트만 실행\n" +
        "• /revise <post_id 또는 파일명 일부>: 특정 리뷰 노트만 실행\n" +
        "• /help: 도움말 표시\n\n" +
        "글 생성은 Gemini 3회 호출을 기준으로 실행됩니다."
    );
    return jsonResponse({ ok: true });
  }

  if (command === "/status") {
    const status = await getOperationsStatus();
    await sendTelegramMessage(chatId, status);
    return jsonResponse({ ok: true });
  }

  if (command === "/reviews") {
    const reviews = await getPendingReviews();
    await sendTelegramMessage(chatId, reviews);
    return jsonResponse({ ok: true });
  }

  if (command === "/revise") {
    const reviewFilter = commandArgs.join(" ").trim();
    await triggerRevisionFromTelegram(chatId, reviewFilter);
    return jsonResponse({ ok: true });
  }

  if (!trimmedText || trimmedText.startsWith("/")) {
    await sendTelegramMessage(
      chatId,
      "알 수 없는 명령어입니다. /help 를 입력하면 사용 가능한 명령어를 볼 수 있습니다."
    );
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── GitHub Actions Trigger ──────────────────────────────────
  console.log(`Triggering GitHub Actions for query: "${trimmedText}"`);

  try {
    await sendTelegramMessage(
      chatId,
      `⚙️ Request received!\n\n📝 Topic: "${trimmedText}"\n\n✍️ The Writer and Editor agents are starting work. Please wait a moment! (usually takes 2–3 minutes)`
    );

    const ghResponse = await triggerGitHubAction(trimmedText, chatId);

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
  return dispatchWorkflow("telegram_trigger.yml", {
    query_input: queryInput,
    chat_id: String(chatId),
  });
}

async function triggerRevisionFromTelegram(chatId, reviewFilter) {
  const label = reviewFilter ? ` (${reviewFilter})` : "";
  await sendTelegramMessage(
    chatId,
    `🧠 Revision request received${label}.\n\nObsidian ready 리뷰 노트를 기준으로 기존 글 보강 workflow를 실행합니다. 완료/실패 결과는 Actions에서 다시 알려드립니다.`
  );

  const ghResponse = await triggerRevisionWorkflow(chatId, reviewFilter);
  if (!ghResponse.ok) {
    const errBody = await ghResponse.text();
    console.error(`GitHub revision dispatch failed: ${ghResponse.status} - ${errBody}`);
    await sendTelegramMessage(
      chatId,
      `❌ Revision workflow 실행에 실패했습니다.\nError code: ${ghResponse.status}`
    );
  }
}

async function triggerRevisionWorkflow(chatId, reviewFilter) {
  return dispatchWorkflow("revise.yml", {
    chat_id: String(chatId),
    review_filter: reviewFilter || "",
  });
}

async function dispatchWorkflow(workflow, inputs) {
  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${workflow}/dispatches`;

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
      inputs,
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

async function getLatestWorkflowRun(workflow) {
  const url = `https://api.github.com/repos/${GITHUB_REPO}/actions/workflows/${workflow}/runs?per_page=1`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "TelegramBlogBot/1.1",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub status API returned ${response.status}`);
  }
  const payload = await response.json();
  return payload.workflow_runs?.[0] || null;
}

async function getGitHubJson(path) {
  const url = `https://api.github.com/repos/${GITHUB_REPO}/${path}`;
  const response = await fetch(url, {
    headers: {
      Authorization: `Bearer ${GITHUB_TOKEN}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "TelegramBlogBot/1.2",
      "X-GitHub-Api-Version": "2022-11-28",
    },
  });
  if (!response.ok) {
    throw new Error(`GitHub API returned ${response.status}`);
  }
  return response.json();
}

function decodeGitHubContent(encoded) {
  const binary = atob((encoded || "").replace(/\n/g, ""));
  const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
  return new TextDecoder("utf-8").decode(bytes);
}

function frontMatterValue(text, key) {
  const match = text.match(new RegExp(`^${key}:\\s*["']?([^"'\\n]+)["']?\\s*$`, "im"));
  return match ? match[1].trim() : "";
}

async function getReviewNoteDetails(item) {
  try {
    const file = await getGitHubJson(`contents/_reviews/pending/${encodeURIComponent(item.name)}?ref=main`);
    const text = decodeGitHubContent(file.content);
    return {
      name: item.name,
      status: frontMatterValue(text, "status") || "unknown",
      target: frontMatterValue(text, "target_post_id") || "unknown",
    };
  } catch (error) {
    return {
      name: item.name,
      status: "unknown",
      target: "unknown",
    };
  }
}

async function getPendingReviews() {
  try {
    const items = await getGitHubJson("contents/_reviews/pending?ref=main");
    const noteItems = (Array.isArray(items) ? items : [])
      .filter((item) => item.type === "file")
      .filter((item) => item.name.endsWith(".md"))
      .filter((item) => !item.name.startsWith("_"))
      .filter((item) => !item.name.startsWith("example-"))
      .sort((left, right) => left.name.localeCompare(right.name));

    if (noteItems.length === 0) {
      return "🧠 Pending review notes가 없습니다.\n\nObsidian에서 `_reviews/pending`에 status: ready 리뷰 노트를 만들면 /revise 로 실행할 수 있습니다.";
    }

    const details = await Promise.all(noteItems.slice(0, 10).map(getReviewNoteDetails));
    const readyCount = details.filter((note) => note.status.toLowerCase() === "ready").length;
    const shown = details
      .map((note) => `• ${note.name} — ${note.status} — ${note.target}`)
      .join("\n");
    const suffix = noteItems.length > 10 ? `\n…and ${noteItems.length - 10} more` : "";
    return (
      "🧠 *Pending review notes*\n\n" +
      `${shown}${suffix}\n\n` +
      `Ready notes shown: ${readyCount}\n\n` +
      "실행:\n" +
      "• `/revise` — ready 리뷰 전체 실행\n" +
      "• `/revise latest` — 가장 최근 ready 리뷰 1개 실행\n" +
      "• `/revise <post_id 또는 파일명 일부>` — 특정 리뷰 실행"
    );
  } catch (error) {
    return `⚠️ Pending review notes를 조회하지 못했습니다.\n\`${error.message}\``;
  }
}

function formatRun(label, run) {
  if (!run) return `• ${label}: 실행 기록 없음`;
  const state = run.status === "completed" ? run.conclusion : run.status;
  return `• ${label}: *${state || "unknown"}*\n  [실행 로그](${run.html_url})`;
}

async function getOperationsStatus() {
  try {
    const [generation, revision, pages] = await Promise.all([
      getLatestWorkflowRun("telegram_trigger.yml"),
      getLatestWorkflowRun("revise.yml"),
      getLatestWorkflowRun("deploy.yml"),
    ]);
    return (
      "📡 *블로그 자동화 운영 상태*\n\n" +
      `${formatRun("최근 글 생성", generation)}\n` +
      `${formatRun("최근 Obsidian 보강", revision)}\n` +
      `${formatRun("최근 Pages 배포", pages)}\n\n` +
      "_정확한 Gemini 무료 잔여량은 API에서 제공되지 않으며, 실행별 사용량은 완료 메시지에서 확인할 수 있습니다._"
    );
  } catch (error) {
    return `⚠️ 운영 상태를 조회하지 못했습니다.\n\`${error.message}\``;
  }
}

function jsonResponse(payload) {
  return new Response(JSON.stringify(payload), {
    headers: { "Content-Type": "application/json" },
  });
}
