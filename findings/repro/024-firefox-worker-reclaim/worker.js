// Classic worker: importScripts an Emscripten MODULARIZE pthread module and
// wait for its runtime (which includes the 7 preloaded pool workers).  The
// page never terminates this worker -- navigation teardown is the path under
// test.
self.onmessage = async (event) => {
  const started = performance.now();
  try {
    const glueUrl = new URL("./minimal.js", self.location.href).href;
    importScripts(glueUrl);
    const moduleInstance = await self.createProbeModule({
      // Without this the pthread pool would try to spawn worker.js again
      // instead of the glue.
      mainScriptUrlOrBlob: glueUrl,
      print: () => {},
      printErr: () => {},
    });
    const ping = moduleInstance.ccall("oxsdk_minimal_ping", "number", [], []);
    const touchMib = (event.data && event.data.touchMib) || 0;
    if (touchMib > 0) {
      // JS-heap ballast owned by this worker, alive until navigation tears
      // the worker down.  This mirrors what a real engine worker holds (file
      // system images, module wire bytes).  Committing pages of the shared
      // wasm memory instead does NOT reproduce -- Firefox reclaims those
      // promptly; it is the dead workers' JS heaps that pile up.
      self.ballast = new Uint8Array(touchMib << 20);
      self.ballast.fill(1);
    }
    self.postMessage({
      ready: true,
      ping,
      heapBytes: moduleInstance.HEAPU8.length,
      initMs: Math.round(performance.now() - started),
    });
  } catch (error) {
    self.postMessage({ ready: false, error: String(error) });
  }
};
