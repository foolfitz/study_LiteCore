// Private r2 diagnostic only; included under OXSDK_E2_V23_DIAGNOSTIC.
void emitOrderedHtml(const char *type, std::uint32_t requestId, const std::string &html) {
  std::ostringstream json;
  json << "{\"type\":\"" << type << "\",\"requestId\":" << requestId
       << ",\"html\":\"" << jsonEscape(html.c_str()) << "\",\"bytes\":" << html.size() << "}";
  emitJson(json.str());
}

void startOrderedHtmlRead(const Command &command) {
  emitOrderedControl(9, command.requestId);
  // Ruling 2026-10-26 / spec20: literal 040 transfer, engine dispatch only.
  // The reply captures owned HTML; it never calls LOK at the next poll.
  std::unique_ptr<char, decltype(&std::free)> text(
      gState.document->pClass->getTextSelection(gState.document, "text/html", nullptr), &std::free);
  const std::string html = text ? text.get() : "";
  emitOrderedHtml("v23-html-return", command.requestId, html);
  setOrderedReply([requestId = command.requestId, html] {
    emitOrderedHtml("v23-html-result", requestId, html);
  });
}
