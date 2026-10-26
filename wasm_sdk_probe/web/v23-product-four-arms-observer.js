// Observation-only entry for the v23 product four arms (instrument, not product).
//
// Served by tools/run_e2_c_product_path.py through a DECLARED mirror that replaces only the
// page's module tag in e2-editor.html; the app, shell, SDK and frozen worker are served
// byte-identical.  The core installs its pass-through wrappers BEFORE the unchanged product app
// is imported, so the app's first Worker and first session are already observed.  It stays
// dormant until the runner's four-arm block calls `__fourArmsControl.begin()`.
import {NarrowEditorV2Session} from './editor-shell-v2/narrow-editor-v2-session.js';
import {installFourArmsObserver} from './v23-product-four-arms-observer-core.js';

installFourArmsObserver(window, {Session: NarrowEditorV2Session});
await import('./e2-editor-app.js');
window.__fourArms.booted = true;
