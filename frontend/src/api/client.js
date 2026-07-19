export async function apiGet(path) {
  const r = await fetch(path, { credentials: "include" });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${r.status})`);
  }
  return r.json();
}

export async function apiPost(path, body) {
  const r = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) {
    const data = await r.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${r.status})`);
  }
  return r.json();
}

/** Consume SSE from POST /api/ask */
export async function askStream(query, { onMeta, onToken, onDone, onError }) {
  return streamPost("/api/ask", { query }, { onMeta, onToken, onDone, onError });
}

/** Expert consultation chat (premium) */
export async function consultationStream(body, { onMeta, onToken, onDone, onError }) {
  return streamPost("/api/premium/consultation/chat", body, {
    onMeta,
    onToken,
    onDone,
    onError,
  });
}

async function streamPost(path, body, { onMeta, onToken, onDone, onError }) {
  const r = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!r.ok) {
    const errBody = await r.json().catch(() => ({}));
    onError?.(new Error(errBody.detail || `Request failed (${r.status})`));
    return;
  }
  const reader = r.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const parts = buf.split("\n\n");
    buf = parts.pop() || "";
    for (const block of parts) {
      const lines = block.split("\n");
      let event = "message";
      let data = "";
      for (const line of lines) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (!data) continue;
      try {
        const parsed = JSON.parse(data);
        if (event === "meta") onMeta?.(parsed);
        else if (event === "token") onToken?.(parsed.text || "");
        else if (event === "done") onDone?.(parsed);
      } catch {
        /* ignore partial */
      }
    }
  }
}
