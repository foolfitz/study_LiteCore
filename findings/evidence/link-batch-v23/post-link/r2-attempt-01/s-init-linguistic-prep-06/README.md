# Uncounted linguistic preparation: transport failure

The first Chrome v22 cell could not retrieve its completed page snapshot: the CDP websocket rejected a frame larger than its existing 1 MiB limit (close 1009). No linguistic page result was retrieved, so this attempt establishes no saved-content, rendering, or comparison outcome. The owned runner was interrupted after that failure; its index also retains the subsequently interrupted r2 cell without a page result. Both records are preserved exactly as written. The count toward the 72-cell comparison remains zero.

The follow-up correction belongs only to the S-init runner: freeze one serialized UTF-8 snapshot, export bounded base64 chunks, and verify reconstructed byte length and SHA-256 before JSON parsing. Raw pixels and wire data remain intact. A fresh attempt is required; this historical output is not repaired or reused.
