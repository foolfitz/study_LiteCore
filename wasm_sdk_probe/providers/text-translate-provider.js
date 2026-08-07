import { descriptor } from "./text-translate-descriptor.js";

export { descriptor };

function abortableDelay(milliseconds, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason || new DOMException("aborted", "AbortError"));
      return;
    }
    const timer = setTimeout(resolve, milliseconds);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason || new DOMException("aborted", "AbortError"));
    }, { once: true });
  });
}

export async function invoke(invocation, context) {
  if (invocation.endpointId !== "translate-selection")
    throw new Error(`unsupported endpoint: ${invocation.endpointId}`);
  if (invocation.input.parameters["target-language"] !== "zh-TW")
    throw new Error("fixture provider only supports target-language=zh-TW");
  context.reportProgress({ fraction: 0.25, message: "selection received" });
  await abortableDelay(100, context.signal);
  context.reportProgress({ fraction: 0.75, message: "translation ready" });
  const text = invocation.input.text === "English words"
    ? "R4 Provider：英文詞彙"
    : `R4 Provider：${invocation.input.text}`;
  context.reportProgress({ fraction: 1, message: "complete" });
  return {
    type: "replaceSelection",
    text,
    expectedRevision: invocation.input.revision,
  };
}

export default Object.freeze({ descriptor, invoke });
