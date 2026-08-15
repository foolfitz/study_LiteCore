#include "format_readback_text.hpp"

#include <cstdio>
#include <string>
#include <vector>

// Generated from the markup the native rounds actually captured, with the
// expected per-block text taken from the PYTHON analyzer that judged those
// rounds.  So this is a cross-implementation check: if the C++ extractor and
// the analyzer ever disagree about real markup, this goes red.
namespace {
struct Case { const char *name; const char *html; std::vector<std::string> expected; };
int gFailures = 0;
void check(const Case &c) {
  const std::vector<std::string> got = probe::extractBlockTexts(c.html);
  if (got == c.expected) return;
  ++gFailures;
  std::printf("FAIL %s: got %zu blocks, expected %zu\n", c.name, got.size(), c.expected.size());
  for (std::size_t i = 0; i < got.size(); ++i)
    std::printf("   got[%zu] = %s\n", i, got[i].c_str());
  for (std::size_t i = 0; i < c.expected.size(); ++i)
    std::printf("   exp[%zu] = %s\n", i, c.expected[i].c_str());
}
} // namespace

int main() {
  const Case cases[] = {
    {"cross-paragraph/check1", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p>\n<p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p>\n</body>\n</html>", {"E1-MULTI-START alpha", "第二段中文"}},
    {"cross-paragraph/check2", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\">\n<ul><li><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p></li>\n\t<li><p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p></li>\n</ul>\n</body>\n</html>", {"E1-MULTI-START alpha", "第二段中文"}},
    {"single-paragraph-control/check1", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START</p>\n</body>\n</html>", {"E1-MULTI-START"}},
    {"single-paragraph-control/check2", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START</p>\n</body>\n</html>", {"E1-MULTI-START"}},
    {"single-paragraph-whole/check1", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p>\n</body>\n</html>", {"E1-MULTI-START alpha"}},
    {"single-paragraph-whole/check2", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\">\n<ul><li><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p></li>\n</ul>\n</body>\n</html>", {"E1-MULTI-START alpha"}},
    {"cross-paragraph-partial-head/check1", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">TART alpha</p>\n<p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p>\n</body>\n</html>", {"TART alpha", "第二段中文"}},
    {"cross-paragraph-partial-head/check2", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\">\n<ul><li><p style=\"line-height: 100%; margin-bottom: 0.08in\">TART alpha</p></li>\n\t<li><p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p></li>\n</ul>\n</body>\n</html>", {"TART alpha", "第二段中文"}},
    {"cross-paragraph-ordered-sample/check1", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\"><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p>\n<p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p>\n</body>\n</html>", {"E1-MULTI-START alpha", "第二段中文"}},
    {"cross-paragraph-ordered-sample/check2", "<!DOCTYPE html>\n<html>\n<head>\n\t<meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"/>\n\t<title></title>\n\t<meta name=\"generator\" content=\"LibreOfficeDev 26.8.0.1.0 (Linux)\"/>\n\t<style type=\"text/css\">\n\t\t@page { size: 8.5in 11in; margin: 0.79in }\n\t\tp { margin-bottom: 0.1in; line-height: 115%; background: transparent }\n\t</style>\n</head>\n<body lang=\"en-US\" link=\"#000080\" vlink=\"#800000\" dir=\"ltr\">\n<ol><li><p style=\"line-height: 100%; margin-bottom: 0.08in\">E1-MULTI-START alpha</p></li>\n\t<li><p style=\"line-height: 100%; margin-bottom: 0.08in\"><font face=\"DejaVu Sans\"><span lang=\"zh-TW\">第二段中文</span></font></p></li>\n</ol>\n</body>\n</html>", {"E1-MULTI-START alpha", "第二段中文"}},
  };
  for (const Case &c : cases) check(c);

  // Controls: the extractor must be able to report a difference.
  if (probe::extractBlockTexts("<body><p>a</p><p>b</p></body>") ==
      probe::extractBlockTexts("<body><p>a</p></body>")) {
    std::printf("FAIL control: a lost block is invisible\n"); ++gFailures;
  }
  if (probe::extractBlockTexts("<body><p>a</p></body>") ==
      probe::extractBlockTexts("<body><p>A</p></body>")) {
    std::printf("FAIL control: a changed character is invisible\n"); ++gFailures;
  }
  if (probe::extractBlockTexts("<body><p>a<font><span>X</span></font></p></body>") !=
      std::vector<std::string>{"aX"}) {
    std::printf("FAIL control: inline markup is not concatenated\n"); ++gFailures;
  }
  if (probe::extractBlockTexts("<body><h1>heading</h1></body>") !=
      std::vector<std::string>{"heading"}) {
    std::printf("FAIL control: h1 is not treated as a block\n"); ++gFailures;
  }
  std::printf(gFailures ? "%d FAILURES\n" : "all %d checks passed\n",
              gFailures ? gFailures : (int)(sizeof(cases)/sizeof(cases[0])) + 4);
  return gFailures ? 1 : 0;
}
