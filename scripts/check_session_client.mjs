// Isolated checks of the actual API client, using Node's TypeScript transformer.
// These do not replace the Vite build or browser/component tests.
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { stripTypeScriptTypes } from "node:module";

const source = await readFile(new URL("../frontend/src/lib/api.ts", import.meta.url), "utf8");
const transformed = stripTypeScriptTypes(source.replaceAll("import.meta.env", "({})"), { mode: "transform" });
const values = new Map();
globalThis.sessionStorage = {
  getItem: (key) => values.get(key) ?? null,
  setItem: (key, value) => values.set(key, value),
  removeItem: (key) => values.delete(key),
};
globalThis.window = new EventTarget();
const api = await import(`data:text/javascript;base64,${Buffer.from(transformed).toString("base64")}`);
let checked = 0;

api.storeToken("current-token");
globalThis.fetch = async (_url, init) => {
  assert.equal(new Headers(init.headers).get("Authorization"), "Bearer current-token");
  return new Response(JSON.stringify({ ok: true }));
};
assert.deepEqual(await api.apiRequest("/private"), { ok: true });
checked++;

for (const status of [200, 401]) {
  api.storeToken("old-token");
  let resolve;
  globalThis.fetch = () => new Promise((done) => { resolve = done; });
  const pending = api.apiRequest("/private");
  api.storeToken("new-token");
  resolve(new Response(JSON.stringify({ private: true }), { status }));
  await assert.rejects(pending, { name: "AbortError" });
  assert.equal(api.getStoredToken(), "new-token");
  checked++;
}

let expirations = 0;
window.addEventListener("blueberry-auth-expired", () => { expirations++; });
globalThis.fetch = async () => new Response("{}", { status: 401 });
await assert.rejects(api.apiRequest("/private"), { status: 401 });
assert.equal(api.getStoredToken(), null);
assert.equal(expirations, 1);
checked++;

globalThis.fetch = async () => new Response("<html>Upload rejected</html>", { status: 413 });
await assert.rejects(api.apiRequest("/upload"), (error) => error.status === 413 && error.message.includes("tamaño"));
checked++;

globalThis.fetch = async () => new Response("Too many requests", { status: 429 });
await assert.rejects(api.apiRequest("/login", {}, { authenticated: false }),
  (error) => error.status === 429 && error.message.includes("intentos"));
checked++;

console.log(`${checked} isolated API client checks passed`);
