#include <cstdlib>
#include <cstring>
#include <functional>
#include <memory>
#include <sstream>
#include <string>
#include <vector>
#include <cstdint>
struct Command { std::uint32_t requestId; };
struct Document;
struct Functions { char *(*getTextSelection)(Document *, const char *, void *); };
struct Document { Functions *pClass; };
struct { Document *document; } gState;
std::vector<std::string> events;
std::function<void()> reply;
int reads = 0;
bool invalid = false;
std::string source = "<img>台";
char *getTextSelection(Document *doc, const char *mime, void *out) {
  if (doc != gState.document || std::string(mime) != "text/html" || out || events != std::vector<std::string>{"entry:9:41"}) invalid = true;
  ++reads;
  return strdup(source.c_str());
}
void emitOrderedControl(int kind, std::uint32_t requestId) { events.push_back("entry:"+std::to_string(kind)+":"+std::to_string(requestId)); }
std::string jsonEscape(const char *text) { return text; }
void emitJson(const std::string &text) { events.push_back(text); }
void setOrderedReply(std::function<void()> f) { reply = std::move(f); }
#include "ordered_diagnostic_html.inc"
int main() {
  Functions functions{getTextSelection}; Document doc{&functions}; gState.document=&doc;
  startOrderedHtmlRead(Command{41});
  if (invalid || reads != 1 || events.size()!=2 || !reply) return 1;
  const std::string witness="{\"type\":\"v23-html-return\",\"requestId\":41,\"html\":\"<img>台\",\"bytes\":8}";
  if (events[1]!=witness) return 1;
  source="changed after LOK return";
  reply();
  if (invalid || reads != 1 || events.size()!=3) return 1;
  const std::string result="{\"type\":\"v23-html-result\",\"requestId\":41,\"html\":\"<img>台\",\"bytes\":8}";
  return events[2]==result ? 0 : 1;
}
