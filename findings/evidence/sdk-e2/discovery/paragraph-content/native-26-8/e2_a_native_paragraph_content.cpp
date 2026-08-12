// E2-A native paragraph-content probe: save the HTML readback for every
// paragraph-content fixture anchor, with controls that make a stale or wrong
// selection visible in the retained JSONL.
//
// Usage: e2-a-native-paragraph-content INSTALL PROFILE_URL OUTDIR DOC_URL SHA256

#define LOK_USE_UNSTABLE_API

#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <string>
#include <thread>

namespace {

std::string jsonEscape(const char *value, std::size_t length) {
  std::string out;
  if (!value)
    return out;
  for (std::size_t index = 0; index < length; ++index) {
    const unsigned char character = static_cast<unsigned char>(value[index]);
    switch (character) {
    case '"': out += "\\\""; break;
    case '\\': out += "\\\\"; break;
    case '\n': out += "\\n"; break;
    case '\r': out += "\\r"; break;
    case '\t': out += "\\t"; break;
    default:
      if (character < 0x20 || character == 0x7f) {
        char buffer[8];
        std::snprintf(buffer, sizeof(buffer), "\\u%04x", character);
        out += buffer;
      } else {
        out += static_cast<char>(character);
      }
    }
  }
  return out;
}

std::string jsonEscape(const std::string &value) {
  return jsonEscape(value.data(), value.size());
}

std::string hex(const char *value, std::size_t length) {
  static const char kDigits[] = "0123456789abcdef";
  std::string out;
  if (!value)
    return out;
  out.reserve(length * 2);
  for (std::size_t index = 0; index < length; ++index) {
    const unsigned char character = static_cast<unsigned char>(value[index]);
    out += kDigits[character >> 4];
    out += kDigits[character & 0x0f];
  }
  return out;
}

bool isValidUtf8NoNul(const char *value, std::size_t length) {
  if (!value)
    return true;
  for (std::size_t index = 0; index < length;) {
    const unsigned char first = static_cast<unsigned char>(value[index]);
    if (first == 0)
      return false;
    if (first <= 0x7f) {
      ++index;
      continue;
    }

    std::size_t continuationCount = 0;
    unsigned int minimum = 0;
    unsigned int codePoint = 0;
    if ((first & 0xe0) == 0xc0) {
      continuationCount = 1;
      minimum = 0x80;
      codePoint = first & 0x1f;
    } else if ((first & 0xf0) == 0xe0) {
      continuationCount = 2;
      minimum = 0x800;
      codePoint = first & 0x0f;
    } else if ((first & 0xf8) == 0xf0) {
      continuationCount = 3;
      minimum = 0x10000;
      codePoint = first & 0x07;
    } else {
      return false;
    }
    if (index + continuationCount >= length)
      return false;
    for (std::size_t offset = 1; offset <= continuationCount; ++offset) {
      const unsigned char continuation =
          static_cast<unsigned char>(value[index + offset]);
      if ((continuation & 0xc0) != 0x80)
        return false;
      codePoint = (codePoint << 6) | (continuation & 0x3f);
    }
    if (codePoint < minimum || codePoint > 0x10ffff ||
        (codePoint >= 0xd800 && codePoint <= 0xdfff))
      return false;
    index += continuationCount + 1;
  }
  return true;
}

struct Rectangle {
  long x = 0, y = 0, width = 0, height = 0;
  bool valid = false;
};

Rectangle gCaret;
std::string gSelectionPayload;
bool gSelectionSeen = false;

void onCallback(int type, const char *payload, void *) {
  if (type == LOK_CALLBACK_TEXT_SELECTION) {
    gSelectionSeen = true;
    gSelectionPayload = payload ? payload : "";
  }
  if (type == LOK_CALLBACK_INVALIDATE_VISIBLE_CURSOR && payload) {
    Rectangle parsed;
    if (std::sscanf(payload, "%ld, %ld, %ld, %ld", &parsed.x, &parsed.y,
                    &parsed.width, &parsed.height) == 4) {
      parsed.valid = true;
      gCaret = parsed;
    }
  }
}

void drain(int milliseconds) {
  std::this_thread::sleep_for(std::chrono::milliseconds(milliseconds));
}

void dispatch(LibreOfficeKitDocument *document, const char *command,
              bool notify, int drainMs = 400) {
  document->pClass->postUnoCommand(document, command, nullptr, notify);
  drain(drainMs);
}

bool positionAtAnchor(LibreOfficeKitDocument *document, const char *anchor) {
  const std::string arguments =
      std::string("{\"SearchItem.SearchString\":{\"type\":\"string\","
                  "\"value\":\"") +
      anchor +
      "\"},\"SearchItem.Backward\":{\"type\":\"boolean\",\"value\":false},"
      "\"SearchItem.Command\":{\"type\":\"unsigned short\",\"value\":0}}";
  document->pClass->postUnoCommand(document, ".uno:GoToStartOfDoc", nullptr,
                                   false);
  drain(400);
  gCaret = Rectangle{};
  gSelectionSeen = false;
  gSelectionPayload.clear();
  document->pClass->postUnoCommand(document, ".uno:ExecuteSearch",
                                   arguments.c_str(), false);
  drain(700);
  Rectangle hit = gCaret;
  if (!hit.valid && gSelectionSeen) {
    Rectangle parsed;
    if (std::sscanf(gSelectionPayload.c_str(), "%ld, %ld, %ld, %ld", &parsed.x,
                    &parsed.y, &parsed.width, &parsed.height) == 4) {
      parsed.valid = true;
      hit = parsed;
    }
  }
  if (!hit.valid)
    return false;
  document->pClass->setTextSelection(document, LOK_SETTEXTSELECTION_RESET,
                                     hit.x, hit.y + hit.height / 2);
  drain(400);
  return true;
}

std::string stripTagsAndNormalizeWhitespace(const std::string &markup) {
  std::string plain;
  plain.reserve(markup.size());
  bool insideTag = false;
  char quote = 0;
  for (char character : markup) {
    if (insideTag) {
      if (quote != 0) {
        if (character == quote)
          quote = 0;
      } else if (character == '"' || character == '\'') {
        quote = character;
      } else if (character == '>') {
        insideTag = false;
      }
      continue;
    }
    if (character == '<') {
      insideTag = true;
      quote = 0;
      continue;
    }
    const unsigned char byte = static_cast<unsigned char>(character);
    if (byte == ' ' || byte == '\t' || byte == '\n' || byte == '\r' ||
        byte == '\f' || byte == '\v') {
      if (!plain.empty() && plain.back() != ' ')
        plain += ' ';
    } else {
      plain += character;
    }
  }
  if (!plain.empty() && plain.back() == ' ')
    plain.pop_back();
  return plain;
}

bool contains(const std::string &markup, const char *needle) {
  return markup.find(needle) != std::string::npos;
}

std::string bodyMarkup(const std::string &markup) {
  const std::size_t body = markup.find("<body");
  if (body == std::string::npos)
    return std::string();
  const std::size_t start = markup.find('>', body);
  if (start == std::string::npos)
    return std::string();
  const std::size_t end = markup.find("</body", start + 1);
  if (end == std::string::npos)
    return std::string();
  return markup.substr(start + 1, end - start - 1);
}

void writeFeatureMarkers(const std::string &markup) {
  struct Marker {
    const char *name;
    const char *needle;
  };
  static const Marker kMarkers[] = {
      {"<a ", "<a "},       {"href=", "href="},
      {"<img", "<img"},     {"<br", "<br"},
      {"<b>", "<b>"},       {"<div", "<div"},
      {"<pre", "<pre"},     {"<blockquote", "<blockquote"},
      {"name=", "name="},   {"<h1", "<h1"},
      {"<h2", "<h2"},       {"<h3", "<h3"},
      {"<h4", "<h4"},       {"<h5", "<h5"},
      {"<h6", "<h6"},       {"<p ", "<p "},
      {"<p>", "<p>"},
      {"<ul", "<ul"},       {"<ol", "<ol"},
      {"<li", "<li"},       {"<i>", "<i>"},
      {"<span", "<span"},   {"<font", "<font"},
      {"<sup", "<sup"},
  };
  std::cout << '{';
  bool first = true;
  for (const Marker &marker : kMarkers) {
    if (!first)
      std::cout << ',';
    first = false;
    std::cout << '"' << jsonEscape(marker.name, std::strlen(marker.name))
              << "\":" << (contains(markup, marker.needle) ? "true" : "false");
  }
  std::cout << '}';
}

void writeFailureRecord(LibreOfficeKitDocument *document,
                        const std::string &label) {
  const int selectionType = document->pClass->getSelectionType(document);
  std::cout << "{\"probe\":\"readback\",\"anchor\":\"" << jsonEscape(label)
            << "\",\"selectionType\":" << selectionType
            << ",\"text\":\"\",\"html\":\"\",\"found\":false"
            << ",\"selected\":"
            << (selectionType == LOK_SELTYPE_NONE ? "false" : "true")
            << ",\"readbackAttempted\":false,\"htmlBytes\":0"
            << ",\"htmlUtf8\":true,\"textUtf8\":true"
            << ",\"anchorTextInReadback\":false"
            << ",\"featureMarkerScope\":\"body\",\"featureMarkers\":";
  writeFeatureMarkers("");
  std::cout << ",\"skipped\":true}\n";
  std::cout.flush();
}

void readAndWrite(LibreOfficeKitDocument *document, const std::string &label,
                  const std::string &anchor) {
  char *html = document->pClass->getTextSelection(document, "text/html",
                                                  nullptr);
  char *text = document->pClass->getTextSelection(
      document, "text/plain;charset=utf-8", nullptr);
  const std::size_t htmlLength = html ? std::strlen(html) : 0;
  const std::size_t textLength = text ? std::strlen(text) : 0;
  const bool htmlUtf8 = isValidUtf8NoNul(html, htmlLength);
  const bool textUtf8 = isValidUtf8NoNul(text, textLength);
  const std::string markup = htmlUtf8 && html ? std::string(html, htmlLength)
                                              : std::string();
  const std::string body = bodyMarkup(markup);
  const std::string normalized = stripTagsAndNormalizeWhitespace(markup);
  const bool anchorTextInReadback =
      htmlUtf8 && normalized.find(anchor) != std::string::npos;
  const int selectionType = document->pClass->getSelectionType(document);

  std::cout << "{\"probe\":\"readback\",\"anchor\":\"" << jsonEscape(label)
            << "\",\"selectionType\":" << selectionType << ",\"text\":\""
            << (textUtf8 ? jsonEscape(text, textLength) : std::string())
            << "\",\"html\":\""
            << (htmlUtf8 ? jsonEscape(html, htmlLength) : std::string())
            << "\",\"found\":true,\"selected\":"
            << (selectionType == LOK_SELTYPE_NONE ? "false" : "true")
            << ",\"readbackAttempted\":true,\"htmlBytes\":" << htmlLength
            << ",\"htmlUtf8\":" << (htmlUtf8 ? "true" : "false")
            << ",\"textUtf8\":" << (textUtf8 ? "true" : "false")
            << ",\"anchorTextInReadback\":"
            << (anchorTextInReadback ? "true" : "false")
            << ",\"featureMarkerScope\":\"body\",\"featureMarkers\":";
  writeFeatureMarkers(body);
  if (!htmlUtf8)
    std::cout << ",\"htmlHex\":\"" << hex(html, htmlLength) << '"';
  if (!textUtf8)
    std::cout << ",\"textHex\":\"" << hex(text, textLength) << '"';
  std::cout << "}\n";
  std::cout.flush();
  std::free(html);
  std::free(text);
}

const char *const kAnchors[] = {
    "PC-PLAIN",      "PC-H2",       "PC-H3",       "PC-H4",
    "PC-H5",         "PC-H6",       "PC-H7",       "PC-H10",
    "PC-PRE",        "PC-QUOTE",    "PC-TITLE",    "PC-SUBTITLE",
    "PC-LINK",       "PC-BOOKMARK", "PC-FOOTNOTE", "PC-COMMENT",
    "PC-IMAGE",      "PC-BREAK",    "PC-CJK-BOLD", "PC-SECTION",
    "PC-LIST-ITEM",
};

const char *const kNegativeControl = "PC-DOES-NOT-EXIST";

} // namespace

int main(int argc, char **argv) {
  if (argc != 6) {
    std::cerr << "expected INSTALL PROFILE_URL OUTDIR DOC_URL SHA256\n";
    return 64;
  }
  setenv("SAL_USE_VCLPLUGIN", "svp", 1);

  LibreOfficeKit *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) {
    std::cerr << "lok_init_2 returned null\n";
    return 2;
  }

  char *version = kit->pClass->getVersionInfo(kit);
  const std::size_t versionLength = version ? std::strlen(version) : 0;
  const bool versionUtf8 = isValidUtf8NoNul(version, versionLength);
  std::cout << "{\"probe\":\"header\",\"libreOfficeVersion\":\""
            << (versionUtf8 ? jsonEscape(version, versionLength) : std::string())
            << "\",\"libreOfficeVersionUtf8\":"
            << (versionUtf8 ? "true" : "false")
            << ",\"fixture\":\"paragraph-content.odt\",\"fixtureSha256\":\""
            << jsonEscape(argv[5], std::strlen(argv[5])) << '"';
  if (!versionUtf8)
    std::cout << ",\"libreOfficeVersionHex\":\""
              << hex(version, versionLength) << '"';
  std::cout << "}\n";
  std::cout.flush();
  std::free(version);

  LibreOfficeKitDocument *document =
      kit->pClass->documentLoad(kit, argv[4]);
  if (!document) {
    std::cout << "{\"probe\":\"document\",\"fixture\":"
                 "\"paragraph-content.odt\",\"loaded\":false}\n";
    std::cout.flush();
    kit->pClass->destroy(kit);
    return 3;
  }

  document->pClass->initializeForRendering(document, "{}");
  document->pClass->registerCallback(document, onCallback, nullptr);
  const int canvas = 256;
  std::string pixels(static_cast<std::size_t>(canvas) * canvas * 4, '\0');
  document->pClass->paintTile(document,
                              reinterpret_cast<unsigned char *>(pixels.data()),
                              canvas, canvas, 0, 0, 3840, 3840);
  drain(500);

  for (const char *anchor : kAnchors) {
    const std::string label = std::string("paragraph-content/") + anchor;
    if (!positionAtAnchor(document, anchor)) {
      writeFailureRecord(document, label);
      continue;
    }
    dispatch(document, ".uno:SelectText", true, 600);
    readAndWrite(document, label, anchor);
  }

  const std::string negativeLabel =
      std::string("paragraph-content/") + kNegativeControl;
  if (!positionAtAnchor(document, kNegativeControl)) {
    writeFailureRecord(document, negativeLabel);
  } else {
    dispatch(document, ".uno:SelectText", true, 600);
    readAndWrite(document, negativeLabel, kNegativeControl);
  }

  document->pClass->destroy(document);
  kit->pClass->destroy(kit);

  // Returns normally.  An earlier revision of this probe called std::_Exit(0)
  // here, on the grounds that this build crashes in process-static teardown
  // while lazily creating the system clipboard.  That did not reproduce: four
  // runs of this exact code with a plain return all exited 0 with 19 records.
  // Leaving the _Exit in would have made the probe's exit status constant, so a
  // real crash later could never be reported -- the runner would print
  // "probe exit: 0" no matter what happened.
  std::cout.flush();
  std::cerr.flush();
  return 0;
}
