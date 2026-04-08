import { openFieldDB } from "./fieldDb.js";

const DRAFT_STORE = "track_drafts";

/** @typedef {{ id: string, roadId: number | null, points: Array<{ lon: number, lat: number, accuracy?: number }>, startedAt: number, updatedAt: number }} TrackDraft */

async function db() {
  return openFieldDB();
}

const CURRENT_ID = "current";

export async function loadTrackDraft() {
  return (await db()).get(DRAFT_STORE, CURRENT_ID);
}

/** @param {Omit<TrackDraft, "id"> & { id?: string }} draft */
export async function saveTrackDraft(draft) {
  const row = {
    id: CURRENT_ID,
    ...draft,
    updatedAt: Date.now(),
  };
  await (await db()).put(DRAFT_STORE, row);
  return row;
}

export async function clearTrackDraft() {
  await (await db()).delete(DRAFT_STORE, CURRENT_ID);
}
