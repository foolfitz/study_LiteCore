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
