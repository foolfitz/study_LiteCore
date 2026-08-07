#ifndef WASM_SDK_PROBE_API_H
#define WASM_SDK_PROBE_API_H

#ifdef __cplusplus
extern "C" {
#endif

/*
 * Version-zero asynchronous C ABI for the WASM SDK probe.
 *
 * JavaScript calls these functions through Module.ccall(). Every command
 * returns immediately; completion and errors are delivered to
 * globalThis.__probe_on_event(json).
 *
 * Stable event shapes used by the R1 web harness:
 *   {"type":"ready"}
 *   {"type":"opened","parts":N,"width":W,"height":H,"tileMode":M}
 *   {"type":"tile","ptr":P,"size":S,"w":W,"h":H}
 *   {"type":"inserted","method":"paste|postKeyEvent"}
 *   {"type":"saved","url":"file:///tmp/out.odt"}
 *   {"type":"closed"}
 *   {"type":"error","where":"open|tile|...","msg":"..."}
 *   {"type":"lok","id":N,"payload":"..."}
 *
 * The tile pointer remains owned by the caller after the tile event. JS must
 * copy ptr..ptr+size from HEAPU8 and then call probe_free(ptr).
 * All strings passed into this API are UTF-8 and are copied before returning.
 */

void probe_start(void);
void probe_open(const char* file_url);
void probe_paint_tile(int x_twips, int y_twips, int w_twips, int h_twips,
                      int canvas_w_px, int canvas_h_px);
void probe_click(int x_twips, int y_twips);
void probe_insert_text(const char* utf8);
void probe_key(int type, int charcode, int keycode);
void probe_save(const char* format);
void probe_close(void);
void probe_free(void* p);

#ifdef __cplusplus
}
#endif

#endif
