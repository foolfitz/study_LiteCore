// Control worker for the E1-C session-depth probe.  It does nothing the SDK
// worker does except exist and answer once, so that a wedge reproduced here is
// attributable to worker churn rather than to anything LibreOffice does.
self.onmessage = async (event) => {
  const request = event.data || {};
  let bufferBytes = 0;
  if (request.compilePath) {
    // compile mode: fetch and compile the real shipped engine wasm, without
    // instantiating it.  This isolates compiled-code accumulation from memory
    // and from anything LibreOffice's startup code does at runtime.
    const started = performance.now();
    const response = await fetch(request.compilePath);
    if (!response.ok)
      throw new Error(`wasm fetch failed with HTTP ${response.status}`);
    const bytes = await response.arrayBuffer();
    const module = await WebAssembly.compile(bytes);
    self.postMessage({
      ready: true,
      wasmBytes: bytes.byteLength,
      exportsCount: WebAssembly.Module.exports(module).length,
      compileMs: Math.round(performance.now() - started),
    });
    return;
  }
  if (request.shared instanceof SharedArrayBuffer) {
    // Pool mode: the page owns the buffer and every worker touches it, the way
    // emscripten's pthread pool all map the module's shared memory.
    new Uint8Array(request.shared, 0, 1)[0] = 1;
    self.postMessage({
      ready: true, bufferBytes: request.shared.byteLength, touchedShared: true,
    });
    return;
  }
  if (request.wasmMemPages > 0) {
    // wasmmem mode: the exact allocation the engine's pthread runtime makes
    // (-sTOTAL_MEMORY=1GB, shared, no growth => initial == maximum), which the
    // buffer/pool rungs do NOT cover: a shared WebAssembly.Memory reserves
    // guarded address space in the wasm engine's own accounting, a plain
    // SharedArrayBuffer does not.
    const memory = new WebAssembly.Memory({
      initial: request.wasmMemPages,
      maximum: request.wasmMemPages,
      shared: true,
    });
    new Uint8Array(memory.buffer, 0, 1)[0] = 1;
    self.postMessage({
      ready: true,
      bufferBytes: memory.buffer.byteLength,
      wasmSharedMemory: true,
    });
    return;
  }
  if (request.bufferMib > 0) {
    // SharedArrayBuffer is the reason the harness needs cross-origin isolation
    // at all; allocating one here keeps that part of the shape without pulling
    // in the engine.
    const shared = new SharedArrayBuffer(request.bufferMib * 1024 * 1024);
    new Uint8Array(shared, 0, 1)[0] = 1;
    bufferBytes = shared.byteLength;
  }
  self.postMessage({ ready: true, bufferBytes });
};
