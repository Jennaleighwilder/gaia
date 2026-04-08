import { useCallback, useEffect, useState } from "react";

/**
 * Live GPS for follow-me dot. Field use: grant browser permission once.
 */
export function useGPS() {
  const [position, setPosition] = useState(null);
  const [error, setError] = useState(null);
  const [watching, setWatching] = useState(false);
  const [id, setId] = useState(null);

  const stop = useCallback(() => {
    if (id != null && navigator.geolocation) {
      navigator.geolocation.clearWatch(id);
      setId(null);
    }
    setWatching(false);
  }, [id]);

  const start = useCallback(() => {
    if (!navigator.geolocation) {
      setError("Geolocation not supported");
      return;
    }
    setError(null);
    setWatching(true);
    const wid = navigator.geolocation.watchPosition(
      (pos) => {
        setPosition({
          lat: pos.coords.latitude,
          lon: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        });
      },
      (err) => setError(err.message),
      { enableHighAccuracy: true, maximumAge: 5000, timeout: 20000 }
    );
    setId(wid);
  }, []);

  useEffect(() => () => stop(), [stop]);

  return { position, error, watching, start, stop };
}
