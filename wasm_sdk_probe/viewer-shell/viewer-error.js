// Typed refusals of the read-only spreadsheet viewer.  A refusal is something
// the viewer DECIDED (wrong document type, a part it cannot show); it is not an
// engine failure, and the page must be able to tell the two apart by `code`.
export class ViewerError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = "ViewerError";
    this.code = code;
    this.details = details;
  }
}
