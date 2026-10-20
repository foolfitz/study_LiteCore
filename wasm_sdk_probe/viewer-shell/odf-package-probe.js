// What the viewer can tell about an ODF package BEFORE any engine is involved
// (specs/SPEC-M4-ods-in-nextcloud.md §5.2; fable's review C6).
//
// ONE QUESTION: does the package's META-INF/manifest.xml declare encryption?
// An encrypted file used to reach the engine and come back as the generic
// LOK_ERROR "loadComponentFromURL returned an empty reference" -- the same code
// and message a truncated zip gets (findings/evidence/m4-ods/04-sweep-v12.json),
// so "refused" said nothing about why.  Asked here, the answer is typed and the
// engine is never started for a file it cannot open.
//
// WHAT THIS IS NOT: a format check.  A package this reader cannot follow (no
// end-of-central-directory record, no manifest, a compression method other than
// stored or deflate, ZIP64) is reported as unreadable and handed to the engine
// as before.  A second zip reader that refused more than LibreOffice does would
// be a new way for the viewer to fail files the engine opens.
//
// Measured 2026-10-20 with the same predicate in Python over the 306-file corpus:
// exactly the three `expect: "refused"` entries are encrypted, none is misjudged,
// none is unreadable.

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;
const LOCAL_SIGNATURE = 0x04034b50;
const EOCD_MIN = 22;
const EOCD_SEARCH = EOCD_MIN + 0xffff;     // the record plus the longest comment
const MANIFEST = "META-INF/manifest.xml";
// A manifest is a few kilobytes; anything near this is not one.
const MANIFEST_MAX_BYTES = 4 * 1024 * 1024;
const ENCRYPTION_DATA = /<(?:[A-Za-z_][\w.-]*:)?encryption-data\b/;

function unreadable(reason) {
  return { readable: false, encrypted: null, reason };
}

function findEndOfCentralDirectory(view) {
  const last = view.byteLength - EOCD_MIN;
  const first = Math.max(0, view.byteLength - EOCD_SEARCH);
  for (let offset = last; offset >= first; offset -= 1) {
    if (view.getUint32(offset, true) === EOCD_SIGNATURE)
      return offset;
  }
  return -1;
}

function findManifestEntry(view, bytes) {
  const eocd = findEndOfCentralDirectory(view);
  if (eocd < 0)
    return { error: "no end-of-central-directory record" };
  const entries = view.getUint16(eocd + 10, true);
  const size = view.getUint32(eocd + 12, true);
  const start = view.getUint32(eocd + 16, true);
  if (entries === 0xffff || size === 0xffffffff || start === 0xffffffff)
    return { error: "ZIP64 is not read here" };
  if (start + size > eocd)
    return { error: "the central directory runs past its end record" };
  const decoder = new TextDecoder();
  let offset = start;
  for (let index = 0; index < entries; index += 1) {
    if (offset + 46 > eocd || view.getUint32(offset, true) !== CENTRAL_SIGNATURE)
      return { error: `central directory entry ${index} is malformed` };
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const name = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    if (name === MANIFEST) {
      return {
        entry: {
          method: view.getUint16(offset + 10, true),
          compressedSize: view.getUint32(offset + 20, true),
          uncompressedSize: view.getUint32(offset + 24, true),
          localOffset: view.getUint32(offset + 42, true),
        },
      };
    }
    offset += 46 + nameLength + extraLength + commentLength;
  }
  return { error: `no ${MANIFEST}` };
}

async function inflateRaw(compressed) {
  const stream = new Blob([compressed]).stream()
    .pipeThrough(new DecompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function manifestText(view, bytes, entry) {
  if (entry.uncompressedSize > MANIFEST_MAX_BYTES || entry.compressedSize > MANIFEST_MAX_BYTES)
    throw new Error(`${MANIFEST} declares ${entry.uncompressedSize} bytes`);
  const local = entry.localOffset;
  if (local + 30 > bytes.byteLength || view.getUint32(local, true) !== LOCAL_SIGNATURE)
    throw new Error("the manifest's local header is not where the directory says");
  const dataStart = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
  const dataEnd = dataStart + entry.compressedSize;
  if (dataEnd > bytes.byteLength)
    throw new Error("the manifest runs past the end of the file");
  // A copy: the caller's buffer is transferred to the engine afterwards, and a
  // stream still holding a view of it would read a detached buffer.
  const compressed = bytes.slice(dataStart, dataEnd);
  let raw;
  if (entry.method === 0)
    raw = compressed;
  else if (entry.method === 8)
    raw = await inflateRaw(compressed);
  else
    throw new Error(`compression method ${entry.method} is not read here`);
  return new TextDecoder().decode(raw);
}

// Never throws: every way of not knowing is `readable: false` with a reason.
export async function probeOdfPackage(buffer) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < EOCD_MIN)
    return unreadable("too short to be a zip");
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  const found = findManifestEntry(view, bytes);
  if (found.error)
    return unreadable(found.error);
  let text;
  try {
    text = await manifestText(view, bytes, found.entry);
  } catch (error) {
    return unreadable(String(error?.message || error));
  }
  return { readable: true, encrypted: ENCRYPTION_DATA.test(text), reason: null };
}
