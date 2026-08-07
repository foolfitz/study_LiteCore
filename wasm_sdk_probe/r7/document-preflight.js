export class DocumentPreflightError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "DocumentPreflightError";
    this.code = code;
    this.details = details;
  }
}

export const DEFAULT_DOCUMENT_LIMITS = Object.freeze({
  maxFileBytes: 5 * 1024 * 1024,
  maxZipEntries: 2048,
  maxUncompressedBytes: 64 * 1024 * 1024,
  maxCompressionRatio: 200,
});

function safeBasename(name) {
  return typeof name === "string"
    && name.length > 0
    && name.length <= 255
    && !name.includes("\0")
    && !name.includes("/")
    && !name.includes("\\")
    && name !== "."
    && name !== "..";
}

function findEndOfCentralDirectory(view) {
  const minimum = Math.max(0, view.byteLength - 65_557);
  for (let offset = view.byteLength - 22; offset >= minimum; offset -= 1) {
    if (view.getUint32(offset, true) === 0x06054b50)
      return offset;
  }
  return -1;
}

function inspectCentralDirectory(bytes, limits) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.byteLength < 22)
    throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP is truncated");
  const eocd = findEndOfCentralDirectory(view);
  if (eocd < 0)
    throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP central directory is missing");
  const entryCount = view.getUint16(eocd + 10, true);
  const centralSize = view.getUint32(eocd + 12, true);
  const centralOffset = view.getUint32(eocd + 16, true);
  if (entryCount > limits.maxZipEntries)
    throw new DocumentPreflightError("DOCUMENT_TOO_LARGE", "ZIP entry limit exceeded", { entryCount });
  if (centralOffset + centralSize > view.byteLength)
    throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP central directory exceeds input");
  const names = [];
  let compressedBytes = 0;
  let uncompressedBytes = 0;
  let offset = centralOffset;
  const decoder = new TextDecoder("utf-8", { fatal: false });
  for (let index = 0; index < entryCount; index += 1) {
    if (offset + 46 > view.byteLength || view.getUint32(offset, true) !== 0x02014b50)
      throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP central entry is invalid", { index });
    const compressed = view.getUint32(offset + 20, true);
    const uncompressed = view.getUint32(offset + 24, true);
    const nameLength = view.getUint16(offset + 28, true);
    const extraLength = view.getUint16(offset + 30, true);
    const commentLength = view.getUint16(offset + 32, true);
    const end = offset + 46 + nameLength + extraLength + commentLength;
    if (end > view.byteLength)
      throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP central entry is truncated", { index });
    const name = decoder.decode(bytes.subarray(offset + 46, offset + 46 + nameLength));
    if (name.startsWith("/") || name.split("/").includes(".."))
      throw new DocumentPreflightError("CORRUPT_DOCUMENT", "ZIP entry path is unsafe", { name });
    names.push(name);
    compressedBytes += Math.max(compressed, 1);
    uncompressedBytes += uncompressed;
    offset = end;
  }
  const ratio = uncompressedBytes / Math.max(1, compressedBytes);
  if (uncompressedBytes > limits.maxUncompressedBytes || ratio > limits.maxCompressionRatio) {
    throw new DocumentPreflightError(
      "DOCUMENT_TOO_LARGE", "ZIP expanded size or compression ratio limit exceeded",
      { uncompressedBytes, compressionRatio: ratio },
    );
  }
  return { entryCount, compressedBytes, uncompressedBytes, compressionRatio: ratio, names };
}

export function preflightDocument(input, options = {}) {
  const bytes = input instanceof Uint8Array ? input : new Uint8Array(input);
  const name = options.name || "document.odt";
  const limits = { ...DEFAULT_DOCUMENT_LIMITS, ...(options.limits || {}) };
  if (!safeBasename(name))
    throw new DocumentPreflightError("INVALID_DOCUMENT_NAME", "document name must be a safe basename");
  if (bytes.byteLength > limits.maxFileBytes) {
    throw new DocumentPreflightError(
      "DOCUMENT_TOO_LARGE", "compressed document size limit exceeded",
      { bytes: bytes.byteLength, maxFileBytes: limits.maxFileBytes },
    );
  }
  const lower = name.toLowerCase();
  if (!lower.endsWith(".odt")) {
    throw new DocumentPreflightError(
      "UNSUPPORTED_FORMAT", "R7 writer-review public capability is ODT-only",
      { extension: lower.includes(".") ? lower.slice(lower.lastIndexOf(".")) : "" },
    );
  }
  const archive = inspectCentralDirectory(bytes, limits);
  const names = new Set(archive.names);
  const looksDocx = names.has("[Content_Types].xml") && names.has("word/document.xml");
  if (looksDocx) {
    throw new DocumentPreflightError(
      "UNSUPPORTED_FORMAT", "DOCX bytes cannot use the ODT-only public capability",
      { detectedFormat: "docx" },
    );
  }
  if (!names.has("mimetype") || !names.has("content.xml")) {
    throw new DocumentPreflightError(
      "CORRUPT_DOCUMENT", "required ODT package entries are missing",
      { missing: ["mimetype", "content.xml"].filter((entry) => !names.has(entry)) },
    );
  }
  return { format: "odt", bytes: bytes.byteLength, archive };
}

