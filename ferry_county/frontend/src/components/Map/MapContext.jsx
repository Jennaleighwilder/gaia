import { createContext, useContext } from "react";

/**
 * @typedef {{ map: import("maplibre-gl").Map | null; mapLoaded: boolean }} MapLibreCtxValue
 */

/** @type {import("react").Context<MapLibreCtxValue>} */
export const MapLibreContext = createContext({ map: null, mapLoaded: false });

export function useMapLibre() {
  return useContext(MapLibreContext);
}
