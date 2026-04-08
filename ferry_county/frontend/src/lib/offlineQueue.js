import { openFieldDB } from "./fieldDb.js";

const STORE = "sync_queue";

async function dbPromise() {
  return openFieldDB();
}

/** @typedef {{ id: string, createdAt: number, body: object }} QueuedSync */

export async function enqueueSync(body) {
  const db = await dbPromise();
  const id = crypto.randomUUID();
  const row = { id, createdAt: Date.now(), body };
  await db.put(STORE, row);
  return row;
}

export async function listQueued() {
  const db = await dbPromise();
  return db.getAll(STORE);
}

export async function removeQueued(id) {
  const db = await dbPromise();
  await db.delete(STORE, id);
}

export async function clearAllQueued() {
  const db = await dbPromise();
  const keys = await db.getAllKeys(STORE);
  await Promise.all(keys.map((k) => db.delete(STORE, k)));
}
