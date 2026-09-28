# richdocuments: the COOP/COEP listener as shipped

Source: local checkout /home/jiajun/OSSII/NC_modules/richdocuments_32, v9.0.2-11-g995fc83e7, read 2026-09-28.
Introduced by commit e9f8d1f37 (2023-10-26, 'feat: Add headers for wasm support').

```php
	public function handle(Event $event): void {
		if (!$event instanceof BeforeTemplateRenderedEvent) {
			return;
		}

		if ($this->capabilitiesService->hasWASMSupport()) {
			$event->getResponse()->addHeader('Cross-Origin-Opener-Policy', 'same-origin');
			$event->getResponse()->addHeader('Cross-Origin-Embedder-Policy', 'require-corp');
		}

		$startPresentation = $this->request->getParam('startPresentation') === 'true';
		$this->initialStateService->providePresentation($startPresentation);
	}
```

Registered for every TemplateResponse: lib/AppInfo/Application.php:89
(`BeforeTemplateRenderedEvent`, dispatched by AdditionalScriptsMiddleware for all apps).

## Correction (2026-09-28, after the counted run)

The date above is the commit's **author** date. `e9f8d1f37` was committed 2023-12-06;
the `hasWASMSupport()` guard shown above came one day later in `571472ebe` (2023-12-07,
"Add headers for wasm support if CO has hasWASMSupport enabled"). The first tag that
contains either is `v8.4.0-beta.1` (2024-03-11); the first final release is `v8.4.0`
(2024-04-24). So the headers reach every app-framework page **only when the Collabora
server advertises WASM support**, and not before spring 2024. Checked with
`git log --format=%cd`, `git tag --contains e9f8d1f37` in the same checkout.
