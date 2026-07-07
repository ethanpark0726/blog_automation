/**
 * Cloudflare Worker: Telegram → GitHub Actions Bridge
 *
 * 역할: 텔레그램 웹훅 POST를 수신하고, GitHub Actions workflow_dispatch를 트리거합니다.
 *
 * 환경변수 (Cloudflare Dashboard > Worker > Settings > Variables):
 *   - TELEGRAM_BOT_TOKEN : BotFather에서 발급받은 텔레그램 봇 토큰
 *   - GITHUB_TOKEN       : GitHub Personal Access Token (repo scope)
 *   - GITHUB_REPO        : "username/repo-name" 형식의 저장소 이름
 *   - ALLOWED_CHAT_ID    : 허용할 텔레그램 채팅 ID (보안용, 문자열)
 */

addEventListener("fetch", (event) => {
  event.respondWith(handleRequest(event.request));
});

async function handleRequest(request) {
  // Cloudflare Worker는 GET 핑 요청도 처리
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

  // ── 메시지 파싱 ─────────────────────────────────────────────
  const message = body?.message || body?.edited_message;
  if (!message) {
    // 텔레그램의 다른 업데이트 유형 (예: inline query) 무시
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  const chatId = String(message?.chat?.id);
  const text = message?.text;

  // ── 보안: 허용된 채팅방 ID만 처리 ───────────────────────────
  if (ALLOWED_CHAT_ID && chatId !== String(ALLOWED_CHAT_ID)) {
    console.log(`Blocked request from unauthorized chat_id: ${chatId}`);
    // 텔레그램에는 200 OK 반환 (무한 재시도 방지)
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── 명령어 필터링 ─────────────────────────────────────────────
  if (!text || text.startsWith("/")) {
    if (text === "/start") {
      await sendTelegramMessage(
        chatId,
        "👋 안녕하세요! 블로그 자동화 봇입니다.\n\n✍️ 블로그로 만들고 싶은 주제나 질문을 입력해 주세요!\n\n예시:\n• `쿠버네티스란 무엇인가?`\n• `양자컴퓨터를 초등학생에게 설명해줘`"
      );
    } else if (text === "/status") {
      await sendTelegramMessage(chatId, "✅ 봇이 정상 작동 중입니다!");
    }
    return new Response(JSON.stringify({ ok: true }), {
      headers: { "Content-Type": "application/json" },
    });
  }

  // ── GitHub Actions 트리거 ─────────────────────────────────────
  console.log(`Triggering GitHub Actions for query: "${text}"`);

  try {
    await sendTelegramMessage(
      chatId,
      `⚙️ 요청을 받았습니다!\n\n📝 주제: "${text}"\n\n✍️ Writer와 Editor 에이전트가 작업을 시작합니다. 잠시만 기다려 주세요! (보통 2~3분 소요)`
    );

    const ghResponse = await triggerGitHubAction(text, chatId);

    if (ghResponse.ok) {
      // GitHub Actions 트리거 성공 (실제 완료 알림은 Actions 워크플로우에서 전송)
      console.log("GitHub Actions triggered successfully");
    } else {
      const errBody = await ghResponse.text();
      console.error(`GitHub API Error: ${ghResponse.status} - ${errBody}`);
      await sendTelegramMessage(
        chatId,
        `❌ GitHub Actions 트리거에 실패했습니다.\n오류 코드: ${ghResponse.status}\n관리자에게 문의하세요.`
      );
    }
  } catch (err) {
    console.error("Error triggering GitHub Actions:", err);
    await sendTelegramMessage(chatId, `❌ 내부 오류가 발생했습니다: ${err.message}`);
  }

  return new Response(JSON.stringify({ ok: true }), {
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * GitHub Actions workflow_dispatch 트리거
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
 * 텔레그램 메시지 전송
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
