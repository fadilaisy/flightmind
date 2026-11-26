/** CAT021 (edition 2.6) items the UI knows how to name. Anything else shows the raw value only. */
export interface ItemMeta {
  id: string;
  name: string;
  /** Null where the item has no unit (identifiers, bit flags). */
  unit: string | null;
  lsb: string | null;
  datum: string | null;
  /** One sentence for the Records tab, from the CAT021 item description. */
  definition?: string;
}

const ITEMS: ItemMeta[] = [
  { id: "I021/010", name: "Data source identification", unit: null, lsb: null, datum: null, definition: "Identification of the ground station that sent the report: SAC is the area, SIC the station." },
  { id: "I021/040", name: "Target report descriptor", unit: null, lsb: null, datum: null, definition: "Characteristics of the target report: address type, altitude reporting capability and flags such as the ground bit." },
  { id: "I021/070", name: "Mode 3/A code", unit: null, lsb: null, datum: "octal, four digits", definition: "Mode 3/A code (the squawk), four octal digits." },
  { id: "I021/071", name: "Time of applicability for position", unit: "s", lsb: "1/128 s", datum: "UTC, since midnight", definition: "Time of applicability of the reported position, in seconds since midnight UTC. LSB is 1/128 s." },
  { id: "I021/080", name: "Target address", unit: null, lsb: null, datum: "24-bit ICAO address", definition: "The 24-bit ICAO aircraft address." },
  { id: "I021/130", name: "Position in WGS-84 coordinates", unit: "°", lsb: "180/2^23 °", datum: "WGS-84", definition: "Latitude and longitude in WGS-84, two's complement. LSB is 180/2^23 degrees." },
  { id: "I021/140", name: "Geometric height", unit: "ft", lsb: "6.25 ft", datum: "WGS-84 ellipsoid", definition: "Minimum height from a plane tangent to the earth's ellipsoid (WGS-84), two's complement, LSB 6.25 ft. Not height above the runway." },
  { id: "I021/145", name: "Flight level", unit: "FL", lsb: "1/4 FL (25 ft)", datum: "barometric, standard pressure 1013.25 hPa", definition: "Flight level relative to standard pressure 1013.25 hPa, two's complement, LSB 1/4 FL." },
  { id: "I021/155", name: "Barometric vertical rate", unit: "ft/min", lsb: "6.25 ft/min", datum: "barometric", definition: "Barometric vertical rate, two's complement, LSB 6.25 ft/min." },
  { id: "I021/160", name: "Airborne ground vector", unit: "kt, °", lsb: "2^-14 NM/s, 360/2^16 °", datum: "ground speed, track angle", definition: "Ground speed and track angle over the ground, from the airborne ground vector." },
  { id: "I021/170", name: "Target identification", unit: null, lsb: null, datum: "6-bit ICAO characters", definition: "Callsign or registration, 8 characters in 6-bit ICAO coding." },
];

const BY_ID = new Map(ITEMS.map((i) => [i.id, i]));

/** The mock API uses plain keys. Each maps to the item that carries it. */
const PLAIN_KEY_ITEM: Record<string, string> = {
  ts: "I021/071",
  lat: "I021/130",
  lon: "I021/130",
  geo_alt_ft: "I021/140",
  baro_alt_ft: "I021/145",
  vertical_rate_fpm: "I021/155",
  ground_speed_kt: "I021/160",
  icao24: "I021/080",
  callsign: "I021/170",
  squawk: "I021/070",
  sac: "I021/010",
  sic: "I021/010",
};

/** The unit of a plain key, where it differs from the item's own unit. */
const PLAIN_KEY_UNIT: Record<string, string> = {
  lat: "°",
  lon: "°",
  baro_alt_ft: "ft",
  geo_alt_ft: "ft",
  vertical_rate_fpm: "ft/min",
  ground_speed_kt: "kt",
};

export function itemMeta(id: string): ItemMeta | undefined {
  return BY_ID.get(id);
}

/** Looks up an item by item id ("I021/130") or by a plain mock key ("lat"). */
export function itemForKey(key: string): ItemMeta | undefined {
  return BY_ID.get(key) ?? BY_ID.get(PLAIN_KEY_ITEM[key] ?? "");
}

export interface DecodedRow {
  /** Unique within a record, e.g. "I021/130.lat". */
  path: string;
  key: string;
  item: ItemMeta | undefined;
  value: string;
  unit: string | null;
}

function show(key: string, v: unknown): string {
  if (v === null || v === undefined) return "no value";
  if (typeof v === "number") {
    const s = key === "lat" || key === "lon" ? v.toFixed(5) : v.toLocaleString("en-US", { maximumFractionDigits: 6 });
    return s.replace("-", "\u2212");
  }
  return String(v);
}

/** One row per key. A nested object (for example lat and lon) gives one row per inner key. */
export function describeDecoded(decoded: Record<string, unknown>): DecodedRow[] {
  const rows: DecodedRow[] = [];
  for (const [key, value] of Object.entries(decoded)) {
    const parent = itemForKey(key);
    if (value !== null && typeof value === "object" && !Array.isArray(value)) {
      for (const [inner, v] of Object.entries(value as Record<string, unknown>)) {
        const item = itemForKey(inner) ?? parent;
        rows.push({
          path: `${key}.${inner}`,
          key: inner,
          item,
          value: show(inner, v),
          unit: PLAIN_KEY_UNIT[inner] ?? item?.unit ?? null,
        });
      }
    } else {
      rows.push({
        path: key,
        key,
        item: parent,
        value: show(key, Array.isArray(value) ? JSON.stringify(value) : value),
        unit: PLAIN_KEY_UNIT[key] ?? parent?.unit ?? null,
      });
    }
  }
  return mergePosition(rows);
}

/** I021/130 carries latitude and longitude together, so they show as one row. */
function mergePosition(rows: DecodedRow[]): DecodedRow[] {
  const lat = rows.find((r) => r.key === "lat");
  const lon = rows.find((r) => r.key === "lon");
  if (!lat || !lon) return rows;
  const merged: DecodedRow = { path: "I021/130", key: "I021/130", item: lat.item, value: `${lat.value}, ${lon.value}`, unit: null };
  const out: DecodedRow[] = [];
  for (const r of rows) {
    if (r === lat) out.push(merged);
    else if (r !== lon) out.push(r);
  }
  return out;
}

/** Datum word for an altitude in the track (alt_ft comes from I021/145). */
export function altitudeDatum(): string {
  return "barometric";
}
