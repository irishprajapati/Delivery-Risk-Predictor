/** Kathmandu Valley map presets — distinct coordinates per location. */
export const VALLEY_MAP_CENTER = { lat: 27.7005, lng: 85.324 };

export const LOCATION_PRESETS = [
  { name: "Jawalakhel, Lalitpur", lat: 27.6744, lng: 85.3123 },
  { name: "Thamel, Kathmandu", lat: 27.7154, lng: 85.3105 },
  { name: "Lokanthali, Bhaktapur", lat: 27.6749, lng: 85.3601 },
  { name: "New Baneshwor, Kathmandu", lat: 27.6915, lng: 85.342 },
  { name: "Kupondole, Lalitpur", lat: 27.6881, lng: 85.3142 },
];

/** Match typed address text to a preset (case-insensitive). */
export function findPresetByAddress(address) {
  const normalized = (address || "").trim().toLowerCase();
  if (!normalized) return null;

  return (
    LOCATION_PRESETS.find((preset) => {
      const presetLower = preset.name.toLowerCase();
      return (
        normalized === presetLower ||
        normalized.includes(presetLower.split(",")[0].trim()) ||
        presetLower.includes(normalized)
      );
    }) || null
  );
}

/** Ensure preset coordinates are unique across the valley presets. */
export function presetsHaveDistinctCoordinates(presets = LOCATION_PRESETS) {
  const keys = presets.map((p) => `${p.lat},${p.lng}`);
  return new Set(keys).size === presets.length;
}
