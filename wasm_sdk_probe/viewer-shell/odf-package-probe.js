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
//
// A SECOND QUESTION (SPEC-M4 addendum 8, finding 158, the owner's 158-A): does
// content.xml hold a form control (`<draw:control`)?  On the wasm core the
// `com.sun.star.form.Forms` service does not exist (HAVE_FEATURE_DBCONNECTIVITY=0),
// so a sheet with a control shape opens and then throws on every paint.  Asked
// here, the file is refused with a typed reason before any engine is started.
// The discriminator is `<draw:control`, not `<office:forms` (LO writes that
// element empty into 49 of 306 corpus files) nor `<form:form` (one corpus file
// has a form without controls and paints fine): over the corpus exactly the five
// files that cannot paint carry `<draw:control`.  content.xml is inflated as a
// STREAM and the scan stops at the first match; a file without controls is read
// to the end (the largest corpus content.xml inflates to 192,781,261 bytes), and
// the session records how long the probe took.

const EOCD_SIGNATURE = 0x06054b50;
const CENTRAL_SIGNATURE = 0x02014b50;
const LOCAL_SIGNATURE = 0x04034b50;
const EOCD_MIN = 22;
const EOCD_SEARCH = EOCD_MIN + 0xffff;     // the record plus the longest comment
const MANIFEST = "META-INF/manifest.xml";
const CONTENT = "content.xml";
// A manifest is a few kilobytes; anything near this is not one.
const MANIFEST_MAX_BYTES = 4 * 1024 * 1024;
const ENCRYPTION_DATA = /<(?:[A-Za-z_][\w.-]*:)?encryption-data\b/;
// The control shape's element.  Prefix-qualified in every ODF writer we have seen
// (`draw:`); a document declaring the draw namespace under another prefix would
// pass -- recorded, not handled (the engine then fails as before).
export const FORM_CONTROL_MARKER = "<draw:control";

function unreadable(reason) {
  return { readable: false, encrypted: null, formControls: null, reason };
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

// The central directory entries for the names asked, by name (a name not in the
// package is simply absent from the result).
function findEntries(view, bytes, names) {
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
  const found = {};
  let offset = start;
  for (let index = 0; index < entries; index += 1) {
    if (offset + 46 > eocd || view.getUint32(offset, true) !== CENTRAL_SIGNATURE)
      return { error: `central directory entry ${index} is malformed` };
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const name = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    if (names.includes(name) && !(name in found)) {
      found[name] = {
        method: view.getUint16(offset + 10, true),
        compressedSize: view.getUint32(offset + 20, true),
        uncompressedSize: view.getUint32(offset + 24, true),
        localOffset: view.getUint32(offset + 42, true),
      };
    }
    offset += 46 + nameLength + extraLength + commentLength;
  }
  return { found };
}

function findManifestEntry(view, bytes) {
  const result = findEntries(view, bytes, [MANIFEST]);
  if (result.error)
    return result;
  return result.found[MANIFEST] ? { entry: result.found[MANIFEST] } : { error: `no ${MANIFEST}` };
}

// The compressed bytes of an entry, as a copy (the caller's buffer is transferred
// to the engine afterwards), with the local header checked against the directory.
function entryData(view, bytes, entry, name) {
  const local = entry.localOffset;
  if (local + 30 > bytes.byteLength || view.getUint32(local, true) !== LOCAL_SIGNATURE)
    throw new Error(`${name}'s local header is not where the directory says`);
  const dataStart = local + 30 + view.getUint16(local + 26, true) + view.getUint16(local + 28, true);
  const dataEnd = dataStart + entry.compressedSize;
  if (dataEnd > bytes.byteLength)
    throw new Error(`${name} runs past the end of the file`);
  if (entry.method !== 0 && entry.method !== 8)
    throw new Error(`compression method ${entry.method} is not read here`);
  return bytes.slice(dataStart, dataEnd);
}

// True when the decoded text of `stream` contains `marker`; stops reading at the
// first match.  A marker split across two chunks is found: the last
// marker.length - 1 characters of each chunk are carried into the next.
export async function streamContains(stream, marker) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let carry = "";
  try {
    for (;;) {
      const { value, done } = await reader.read();
      const text = carry + decoder.decode(value, { stream: !done });
      if (text.includes(marker)) {
        await reader.cancel().catch(() => {});
        return true;
      }
      if (done)
        return false;
      carry = text.slice(Math.max(0, text.length - (marker.length - 1)));
    }
  } finally {
    reader.releaseLock?.();
  }
}

async function contentHasFormControls(view, bytes, entry) {
  const compressed = entryData(view, bytes, entry, CONTENT);
  let stream = new Blob([compressed]).stream();
  if (entry.method === 8)
    stream = stream.pipeThrough(new DecompressionStream("deflate-raw"));
  return streamContains(stream, FORM_CONTROL_MARKER);
}

async function inflateRaw(compressed) {
  const stream = new Blob([compressed]).stream()
    .pipeThrough(new DecompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function manifestText(view, bytes, entry) {
  if (entry.uncompressedSize > MANIFEST_MAX_BYTES || entry.compressedSize > MANIFEST_MAX_BYTES)
    throw new Error(`${MANIFEST} declares ${entry.uncompressedSize} bytes`);
  const compressed = entryData(view, bytes, entry, "the manifest");
  const raw = entry.method === 0 ? compressed : await inflateRaw(compressed);
  return new TextDecoder().decode(raw);
}

// Never throws: every way of not knowing is `readable: false` with a reason
// (the manifest), or `formControls: null` with the reason (content.xml alone).
// `readable` is about the manifest, as before; an encrypted package's
// content.xml is ciphertext and is not scanned.
export async function probeOdfPackage(buffer) {
  if (!(buffer instanceof ArrayBuffer) || buffer.byteLength < EOCD_MIN)
    return unreadable("too short to be a zip");
  const bytes = new Uint8Array(buffer);
  const view = new DataView(buffer);
  const found = findEntries(view, bytes, [MANIFEST, CONTENT]);
  if (found.error)
    return unreadable(found.error);
  if (!found.found[MANIFEST])
    return unreadable(`no ${MANIFEST}`);
  let text;
  try {
    text = await manifestText(view, bytes, found.found[MANIFEST]);
  } catch (error) {
    return unreadable(String(error?.message || error));
  }
  const encrypted = ENCRYPTION_DATA.test(text);
  if (encrypted)
    return { readable: true, encrypted: true, formControls: null, reason: null };
  if (!found.found[CONTENT])
    return { readable: true, encrypted: false, formControls: null, reason: `no ${CONTENT}` };
  try {
    const formControls = await contentHasFormControls(view, bytes, found.found[CONTENT]);
    return { readable: true, encrypted: false, formControls, reason: null };
  } catch (error) {
    return { readable: true, encrypted: false, formControls: null, reason: String(error?.message || error) };
  }
}
