// Classic worker for the `minimal` and `realinstant` rungs of the finding 023
// session-depth ladder.  It mirrors sdk-worker.js's load path exactly --
// importScripts of an emscripten MODULARIZE glue, then createProbeModule with
// mainScriptUrlOrBlob so the pthread pool spawns the glue and not this file --
// while doing none of what the SDK does afterwards (no resource packs, no
// oxsdk_engine_start).  The requested ping export is called once so the rung
// can prove the instance answered, not merely resolved.
self.onmessage = async (event) => {
  const request = event.data || {};
  try {
    const started = performance.now();
    // environment.js (the engine's pre-js) expects this hook to exist.
    self.__probe_on_event = () => {};
    // The real profile's FS pre-js fetches soffice.data during runtime init,
    // and only the manifest knows where that lives (artifactFiles).  Resolve
    // against the manifest URL, exactly as sdk-worker.js resolves against its
    // own location inside the profile directory; without this mapping the data
    // fetch 404s and runtime init hangs on its run dependency forever.
    let artifactFiles = {};
    let resolveBase = self.location.href;
    if (request.manifestPath) {
      const manifestUrl = new URL(request.manifestPath, self.location.href).href;
      const response = await fetch(manifestUrl);
      if (!response.ok)
        throw new Error(`manifest fetch failed with HTTP ${response.status}`);
      artifactFiles = (await response.json()).artifactFiles || {};
      resolveBase = manifestUrl;
    }
    const glueUrl = new URL(
      artifactFiles["probe.js"] || request.gluePath, resolveBase,
    ).href;
    importScripts(glueUrl);
    if (typeof self.createProbeModule !== "function")
      throw new Error(`${request.gluePath} did not expose createProbeModule`);
    const moduleInstance = await self.createProbeModule({
      mainScriptUrlOrBlob: glueUrl,
      print: () => {},
      printErr: () => {},
      // Mapped names resolve like sdk-worker.js (against the profile
      // directory); unmapped names resolve next to the glue, which is where
      // emscripten's default locateFile would look.
      locateFile: (path) => (artifactFiles[path]
        ? new URL(artifactFiles[path], resolveBase).href
        : new URL(path, glueUrl).href),
    });
    const ping = moduleInstance.ccall(request.pingExport, "number", [], []);
    self.postMessage({
      ready: true,
      ping,
      heapBytes: moduleInstance.HEAPU8.length,
      initMs: Math.round(performance.now() - started),
    });
  } catch (error) {
    self.postMessage({ ready: false, error: String(error?.stack || error) });
  }
};
