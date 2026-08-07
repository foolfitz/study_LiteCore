// LibreOffice's Emscripten soffice startup unconditionally initializes its
// JavaScript UNO bridge.  The narrow LOK probe intentionally does not ship
// unoembind or uno.js, so bypass that unrelated startup hook at link time.
extern "C" void __wrap__Z18initJsUnoScriptingv() {}
