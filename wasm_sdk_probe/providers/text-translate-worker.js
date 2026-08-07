import { installProviderWorkerRuntime } from "../provider-sdk/provider-sdk.js";
import { descriptor, invoke } from "./text-translate-provider.js";

installProviderWorkerRuntime(globalThis, { descriptor, invoke });
