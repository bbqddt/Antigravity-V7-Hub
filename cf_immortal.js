const TOKEN = '8516319664:AAGHq93N4uliC1QLeltXXD1dBtikguGnMnQ';
const CHAT_ID = '784753298';

async function handleRequest(request) {
  if (request.method === 'POST') {
    try {
      const payload = await request.json();
      if (payload.message && payload.message.text) {
        const text = payload.message.text.toLowerCase();
        
        // Response logic
        if (text.includes('/status')) {
          await sendToTelegram('💠 *离岸态势*: Cloudflare Immortal Node Active\n状态：7*24 绝对理性 (Tokyo Redirect)');
        } else if (text.includes('/strike') || text.includes('计算')) {
          await sendToTelegram('🔱 *Antigravity 26049 期推演*:\n红球: [02, 09, 15, 23, 28, 31]\n蓝球: [06]\n战略: 流形频谱对冲已就绪。');
        }
      }
    } catch (e) {}
  }
  return new Response('OK');
}

async function sendToTelegram(text) {
  const url = `https://api.telegram.org/bot${TOKEN}/sendMessage`;
  await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ chat_id: CHAT_ID, text: text, parse_mode: 'Markdown' })
  });
}

addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request));
});
