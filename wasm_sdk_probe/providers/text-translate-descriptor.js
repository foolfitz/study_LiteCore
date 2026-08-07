export const descriptor = Object.freeze({
  contractVersion: "1.0",
  id: "tw.oxoffice.fixture.translator",
  version: "1.0.0",
  displayName: "OxOffice R4 Fixture Translator",
  capabilities: Object.freeze(["text.translate"]),
  endpoints: Object.freeze([Object.freeze({
    id: "translate-selection",
    capability: "text.translate",
    input: "selection.text",
    outputOperations: Object.freeze(["replaceSelection"]),
  })]),
});

export default descriptor;
