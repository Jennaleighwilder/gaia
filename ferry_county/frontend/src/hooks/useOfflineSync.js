import { useCallback, useEffect, useRef, useState } from "react";
import { enqueueSync, listQueued, removeQueued } from "../lib/offlineQueue.js";
import { postSyncOperation } from "../api.js";

/** Apply track → treatment → waypoint so server can resolve client_track_operation_id. */
const ENTITY_ORDER = { track: 0, treatment: 1, waypoint: 2 };

function sortQueueRows(rows) {
  return [...rows].sort((a, b) => {
    const ta = a.body?.entity_type?.toLowerCase() ?? "";
    const tb = b.body?.entity_type?.toLowerCase() ?? "";
    const ra = ENTITY_ORDER[ta] ?? 50;
    const rb = ENTITY_ORDER[tb] ?? 50;
    if (ra !== rb) return ra - rb;
    return (a.createdAt ?? 0) - (b.createdAt ?? 0);
  });
}

/**
 * Queue offline sync ops (IndexedDB) and flush to POST /sync/operations when online.
 * @param {string} actor — forwarded as X-Actor for audit (matches treatment POST).
 */
export function useOfflineSync(actor) {
  const [pending, setPending] = useState(0);
  const [lastError, setLastError] = useState(null);
  const [flushing, setFlushing] = useState(false);

  const refresh = useCallback(async () => {
    const rows = await listQueued();
    setPending(rows.length);
  }, []);

  /**
   * @param {string} entityType — e.g. "treatment" | "track"
   * @param {string} operation — e.g. "create"
   * @param {object} payload — server schema (flat JSON for treatments includes road_id)
   * @param {string} clientOperationId — stable UUID for idempotency
   */
  const queueSync = useCallback(
    async (entityType, operation, payload, clientOperationId) => {
      const body = {
        client_operation_id: clientOperationId,
        entity_type: entityType,
        operation,
        payload,
      };
      if (!navigator.onLine) {
        await enqueueSync(body);
        await refresh();
        return { queued: true };
      }
      try {
        const res = await postSyncOperation(body, actor);
        return { queued: false, result: res };
      } catch (e) {
        await enqueueSync(body);
        await refresh();
        return { queued: true, error: String(e) };
      }
    },
    [refresh, actor]
  );

  const flush = useCallback(async () => {
    if (!navigator.onLine) return;
    setFlushing(true);
    setLastError(null);
    try {
      const rows = await listQueued();
      const sorted = sortQueueRows(rows);
      for (const row of sorted) {
        try {
          await postSyncOperation(row.body, actor);
          await removeQueued(row.id);
        } catch (e) {
          const msg = String(e?.message || e);
          const code = msg.match(/^(\d{3})\s/)?.[1];
          if (code === "422") {
            await removeQueued(row.id);
            continue;
          }
          setLastError(msg);
          break;
        }
      }
      await refresh();
    } finally {
      setFlushing(false);
    }
  }, [refresh, actor]);

  const flushRef = useRef(flush);
  flushRef.current = flush;

  useEffect(() => {
    refresh();
    const onOnline = () => {
      flushRef.current();
    };
    window.addEventListener("online", onOnline);
    return () => window.removeEventListener("online", onOnline);
  }, [refresh]);

  return {
    pending,
    lastError,
    flushing,
    refresh,
    flush,
    queueSync,
  };
}
