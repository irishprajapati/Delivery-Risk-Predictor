import {
  LOCATION_PRESETS,
  findPresetByAddress,
  presetsHaveDistinctCoordinates,
} from "../src/utils/locationPresets.js";

let failed = 0;

function assert(condition, message) {
  if (!condition) {
    console.error(`FAIL: ${message}`);
    failed += 1;
  } else {
    console.log(`PASS: ${message}`);
  }
}

assert(presetsHaveDistinctCoordinates(), "all presets have distinct coordinates");

const thamel = findPresetByAddress("Thamel, Kathmandu");
assert(thamel?.name === "Thamel, Kathmandu", "Thamel address resolves to Thamel preset");
assert(thamel.lat !== 27.6744 || thamel.lng !== 85.3123, "Thamel is not Jawalakhel coordinates");

const jawalakhel = findPresetByAddress("Jawalakhel");
assert(jawalakhel?.name === "Jawalakhel, Lalitpur", "Jawalakhel address resolves correctly");

const lokanthali = findPresetByAddress("Lokanthali, Bhaktapur");
assert(lokanthali?.lng > 85.34, "Bhaktapur preset has eastern longitude");

assert(LOCATION_PRESETS.length >= 3, "at least three valley presets configured");

if (failed > 0) {
  process.exit(1);
}

console.log("All location preset checks passed.");
