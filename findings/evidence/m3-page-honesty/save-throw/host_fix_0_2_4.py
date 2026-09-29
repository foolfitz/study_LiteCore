"""Host 0.2.4: a save never ends with the bytes nowhere (study_LiteCore review
2026-09-29 of the page-honesty implementation, BLOCKING 1).

    host_fix_0_2_4.py b   the catch-all only (no version bump) -- measured alone
    host_fix_0_2_4.py a   the token that was sent, and version 0.2.4 (after b)
"""
import sys
from pathlib import Path

STEP = sys.argv[1]
ROOT = Path.home() / "Projects/Nextcloud_Apps/litecore"

PART_A = [
("""	// performance.now() when our previous PUT to the file was answered.
	let lastAnswered = null
""", """	// performance.now() when our previous PUT to the file was answered.
	let lastAnswered = null
	// The lock token our latest PUT carried, if any. Not `token`: a refresh
	// answered while that PUT was out can drop `token` to null (loseLock).
	let sentToken = null
"""),
("""	async function tokenOnServer(held) {
		const response = await send(config.file.davUrl, {""", """	async function tokenOnServer(held) {
		if (!held) return false
		const response = await send(config.file.davUrl, {"""),
("""		const extra = { 'Content-Type': ODT, 'If-Match': etag }
		if (token) extra.If = `(${token})`
""", """		const extra = { 'Content-Type': ODT, 'If-Match': etag }
		if (token) extra.If = `(${token})`
		sentToken = token
"""),
("""		if (response.status === 412 && record.attempts[0].withToken) {
			record.tokenOnServer = await tokenOnServer(token)""", """		if (response.status === 412 && record.attempts[0].withToken) {
			// The token that went out, not `token`: if a refresh lost the lock
			// while the PUT was on the wire, `token` is null here, and asking
			// about null threw -- the save ended with no copy and nothing
			// stranded, and leaving was not asked about (study_LiteCore
			// probe_m3_save_throw.py).
			record.tokenOnServer = await tokenOnServer(sentToken)"""),
]

PART_B = [
("""			etag = record.etag
			lastSha = record.sha256
			unstrand('saved')
			return""", """			etag = record.etag
			lastSha = record.sha256
			unstrand('saved')
			record.outcome = 'saved'
			return"""),
("""		if (!record.conflictCopy.failed) {
			unstrand('copy')
			throw failure(code, `${why}你的內容另存為「${record.conflictCopy.name}」。`)
		}
		strand(bytes, record.sha256)
		throw failure(""", """		if (!record.conflictCopy.failed) {
			unstrand('copy')
			record.outcome = 'copy'
			throw failure(code, `${why}你的內容另存為「${record.conflictCopy.name}」。`)
		}
		strand(bytes, record.sha256)
		record.outcome = 'stranded'
		throw failure("""),
("""			inFlight++
			try {
				await saveOnce(bytes, record)
			} finally {""", """			inFlight++
			try {
				await saveOnce(bytes, record)
			} catch (error) {
				// Every save ends one of three ways: the original written, a copy
				// written, or the bytes kept here with leaving guarded -- the page
				// counts on it (study_LiteCore SPEC-M3-page-honesty §7.1). A throw
				// that is none of those (a bug, an answer nobody expected) keeps
				// the bytes rather than let them go.
				if (record.outcome) throw error
				record.unexpected = `${error && error.name}: ${error && error.message}`
				strand(bytes, record.sha256 || null)
				record.outcome = 'stranded'
				throw failure('HOST_SAVE_FAILED', '存回時發生未預期的錯誤：內容還在這個頁面裡，請按「下載這份內容」。')
			} finally {"""),
]

path = ROOT / "js/litecore-editor.js"
text = path.read_text()
for old, new in {"a": PART_A, "b": PART_B}[STEP]:
    assert text.count(old) == 1, old[:80]
    text = text.replace(old, new)
path.write_text(text)
if STEP == "a":
    info = ROOT / "appinfo/info.xml"
    xml = info.read_text()
    assert xml.count("<version>0.2.3</version>") == 1
    info.write_text(xml.replace("<version>0.2.3</version>", "<version>0.2.4</version>"))
print("applied", STEP)
