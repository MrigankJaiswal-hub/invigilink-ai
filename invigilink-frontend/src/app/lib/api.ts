
// src/app/lib/api.ts

// Resolve API base:
// 1) Use env if provided
// 2) Otherwise infer from current browser host (works on LAN IPs and localhost)
export const API_BASE =
  (process.env.NEXT_PUBLIC_API_BASE &&
    process.env.NEXT_PUBLIC_API_BASE.replace(/\/$/, "")) ||
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8080`
    : "http://localhost:8080");

// Read token from localStorage (stored by TokenInput)
function bearer() {
  try {
    const t = localStorage.getItem("invigilink_token");
    return t ? `Bearer ${t}` : "";
  } catch {
    return "";
  }
}

// Core fetch with unified error handling
async function apiFetch(path: string, init?: RequestInit) {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const auth = bearer();

  // Merge headers in a type-safe way
  const headers: HeadersInit = {
    ...(init?.headers || {}),
    ...(auth ? { Authorization: auth } : {}),
  };

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "omit",
    mode: "cors",
  });

  if (!res.ok) {
    // Prefer backend’s JSON {detail:"..."} errors
    const txt = await res.text().catch(() => "");
    try {
      const j = JSON.parse(txt);
      const msg = j?.detail || txt || res.statusText;
      throw new Error(msg);
    } catch {
      throw new Error(txt || res.statusText);
    }
  }
  return res;
}

// ---------- JSON helpers ----------
export async function getJson<T>(path: string): Promise<T> {
  const res = await apiFetch(path, { method: "GET" });
  return res.json() as Promise<T>;
}

export async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  return res.json() as Promise<T>;
}

// ---------- Form-data helper ----------
export async function postForm<T = any>(path: string, formData: FormData): Promise<T> {
  const res = await apiFetch(path, { method: "POST", body: formData });
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  // non-JSON? Return undefined (most import endpoints return JSON though)
  return undefined as unknown as T;
}

// ---------- Binary helpers ----------
/** Fetches a Blob with Authorization (for protected routes). */
export async function getBinary(path: string): Promise<Blob> {
  const res = await apiFetch(path, { method: "GET" });
  return res.blob();
}

/** Extract filename from Content-Disposition if present. */
function filenameFromDisposition(disp: string | null | undefined): string | null {
  if (!disp) return null;
  // filename="foo.pdf" or filename*=UTF-8''foo.pdf
  const mQuoted = /filename="([^"]+)"/i.exec(disp);
  if (mQuoted?.[1]) return mQuoted[1];
  const mUtf = /filename\*=\s*UTF-8''([^;]+)/i.exec(disp);
  if (mUtf?.[1]) return decodeURIComponent(mUtf[1]);
  return null;
}

/**
 * Reliable download that respects server headers:
 * - Uses Authorization
 * - Reads Content-Disposition to get server-provided filename
 * - If Content-Type is HTML, forces .html extension (fixes “invalid PDF” in browsers)
 */
export async function downloadToDisk(path: string, fallbackName = "download") {
  const res = await apiFetch(path, { method: "GET" });
  const blob = await res.blob();
  const ct = (res.headers.get("content-type") || "").toLowerCase();
  const disp = res.headers.get("content-disposition") || "";
  let name = filenameFromDisposition(disp) || fallbackName;

  // If server returned HTML (e.g., PDF engines unavailable), ensure .html
  if (ct.includes("text/html") && !name.toLowerCase().endsWith(".html")) {
    name = name.replace(/\.pdf$/i, "") + ".html";
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.style.display = "none";
  document.body.appendChild(a);
  requestAnimationFrame(() => {
    a.click();
    setTimeout(() => {
      a.remove();
      URL.revokeObjectURL(url);
    }, 0);
  });
}

/**
 * Backward compatible wrapper.
 * If you were calling downloadBinary(path, "file.pdf") this will now
 * honor Content-Type and adjust the extension when needed.
 */
export async function downloadBinary(path: string, filename: string) {
  await downloadToDisk(path, filename);
}
