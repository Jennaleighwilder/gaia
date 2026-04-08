import { openDB } from "idb";

const DB_NAME = "ferry-cwdg-field";
const DB_VER = 3;

/**
 * Single IndexedDB for Field PWA: sync queue + track draft persistence + map snapshot cache.
 */
export function openFieldDB() {
  return openDB(DB_NAME, DB_VER, {
    upgrade(db, oldVersion) {
      if (!db.objectStoreNames.contains("sync_queue")) {
        db.createObjectStore("sync_queue", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("track_drafts")) {
        db.createObjectStore("track_drafts", { keyPath: "id" });
      }
      if (oldVersion < 3 && !db.objectStoreNames.contains("cache")) {
        db.createObjectStore("cache", { keyPath: "key" });
      }
    },
  });
}
