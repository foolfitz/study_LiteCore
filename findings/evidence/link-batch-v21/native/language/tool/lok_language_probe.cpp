// Scratch probe (link batch v21, Language= characterisation; not product code).
//
// Same LOK calls as probe-1's lok_defaults_probe.cpp: lok_init_2(install, profile), then
// documentLoad(url) or documentLoadWithOptions(url, options), then saveAs(out, "odt", nullptr).
// Added: in-process readouts of what the engine believes, printed at two moments
// ("after-init" = after lok_init_2 returned, so Desktop::Main / prepareLocale has run;
// "after-load" = after the document load returned). The readouts only read.
//
// Optional (env PROBE_DATE_FIELD=1): after the load, dispatch .uno:InsertDateField, then
// .uno:SelectAll, print the selection as text/plain, then save (for Q5).
//
// Mutation control (env PROBE_FORCE_WESTERN_FALLBACK=<bcp47>): see main().
//
// Usage: lok_language_probe <install-dir> <profile-url> <in-url> <out-path> [options]
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>

#include <sal/config.h>
#include <rtl/ustring.hxx>
#include <com/sun/star/i18n/ScriptType.hpp>
#include <i18nlangtag/lang.h>
#include <i18nlangtag/languagetag.hxx>
#include <i18nlangtag/mslangid.hxx>
#include <i18nutil/paper.hxx>
#include <comphelper/lok.hxx>
#include <officecfg/Office/Linguistic.hxx>
#include <officecfg/Setup.hxx>
#include <officecfg/System.hxx>
#include <tools/date.hxx>
#include <unotools/localedatawrapper.hxx>
#include <unotools/syslocale.hxx>

#include <clocale>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <unistd.h>

extern char **environ;

namespace {

std::string u8(const OUString &s) { return OUStringToOString(s, RTL_TEXTENCODING_UTF8).getStr(); }

std::string tag(LanguageType n) { return u8(LanguageTag::convertToBcp47(n)) + "(0x" + [n] {
    char b[8]; std::snprintf(b, sizeof b, "%04x", static_cast<unsigned>(static_cast<sal_uInt16>(n))); return std::string(b); }() + ")"; }

template <typename T> std::string cfg() {
    try { return "\"" + u8(T::get()) + "\""; } catch (...) { return "(exception)"; }
}

void readout(const char *phase) {
    namespace ST = css::i18n::ScriptType;
    std::printf("[%s] glibc setlocale(LC_ALL,NULL)=%s\n", phase, std::setlocale(LC_ALL, nullptr));
    std::printf("[%s] cfg System/L10N Locale=%s SystemLocale=%s UILocale=%s\n", phase,
                cfg<officecfg::System::L10N::Locale>().c_str(),
                cfg<officecfg::System::L10N::SystemLocale>().c_str(),
                cfg<officecfg::System::L10N::UILocale>().c_str());
    std::printf("[%s] cfg Setup/L10N ooSetupSystemLocale=%s ooLocale=%s\n", phase,
                cfg<officecfg::Setup::L10N::ooSetupSystemLocale>().c_str(),
                cfg<officecfg::Setup::L10N::ooLocale>().c_str());
    std::printf("[%s] cfg Linguistic/General DefaultLocale=%s _CJK=%s _CTL=%s\n", phase,
                cfg<officecfg::Office::Linguistic::General::DefaultLocale>().c_str(),
                cfg<officecfg::Office::Linguistic::General::DefaultLocale_CJK>().c_str(),
                cfg<officecfg::Office::Linguistic::General::DefaultLocale_CTL>().c_str());
    std::printf("[%s] MsLangId configuredSystemLanguage=%s configuredSystemUILanguage=%s\n", phase,
                tag(MsLangId::getConfiguredSystemLanguage()).c_str(),
                tag(MsLangId::getConfiguredSystemUILanguage()).c_str());
    // The three configured fallbacks, read through the public resolver: a language whose
    // script differs from the requested script type returns that type's fallback
    // (mslangid.cxx resolveSystemLanguageByScriptType). An unset fallback reads as the
    // built-in default (en-US / zh-CN / hi-IN) and cannot be told apart from an explicit one.
    std::printf("[%s] fallbacks western=%s asian=%s complex=%s\n", phase,
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_JAPANESE, ST::LATIN)).c_str(),
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_ENGLISH_US, ST::ASIAN)).c_str(),
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_ENGLISH_US, ST::COMPLEX)).c_str());
    // What SwDoc's constructor computes for an empty DefaultLocale (LANGUAGE_SYSTEM).
    std::printf("[%s] resolve(SYSTEM) latin=%s asian=%s complex=%s\n", phase,
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_SYSTEM, ST::LATIN)).c_str(),
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_SYSTEM, ST::ASIAN)).c_str(),
                tag(MsLangId::resolveSystemLanguageByScriptType(LANGUAGE_SYSTEM, ST::COMPLEX)).c_str());
    std::printf("[%s] LOK languageTag=%s locale=%s\n", phase,
                u8(comphelper::LibreOfficeKit::getLanguageTag().getBcp47(false)).c_str(),
                u8(comphelper::LibreOfficeKit::getLocale().getBcp47(false)).c_str());
    PaperInfo p = PaperInfo::getSystemDefaultPaper();
    std::printf("[%s] PaperInfo::getSystemDefaultPaper paper=%d %ldx%ld (1/100 mm)\n", phase,
                static_cast<int>(p.getPaper()), p.getWidth(), p.getHeight());
    SvtSysLocale sys;
    const LocaleDataWrapper &ld = sys.GetLocaleData();
    std::printf("[%s] SvtSysLocale languageTag=%s localeData=%s currSymbol=\"%s\" bank=\"%s\" "
                "decimalSep=\"%s\" dateSep=\"%s\" date(2026-10-16)=\"%s\"\n", phase,
                u8(sys.GetLanguageTag().getBcp47(false)).c_str(),
                u8(ld.getLanguageTag().getBcp47(false)).c_str(),
                u8(ld.getCurrSymbol()).c_str(), u8(ld.getCurrBankSymbol()).c_str(),
                u8(ld.getNumDecimalSep()).c_str(), u8(ld.getDateSep()).c_str(),
                u8(ld.getDate(Date(16, 10, 2026))).c_str());
    std::fflush(stdout);
}

} // namespace

int main(int argc, char **argv) {
    if (argc < 5) { std::fprintf(stderr, "usage\n"); return 2; }
    const char *install = argv[1], *profile = argv[2], *inUrl = argv[3], *outPath = argv[4];
    const char *options = argc > 5 ? argv[5] : nullptr;
    std::printf("args options=%s\n", options ? options : "(none)");
    for (char **e = environ; *e; ++e)
        if (!std::strncmp(*e, "LANG", 4) || !std::strncmp(*e, "LC_", 3) || !std::strncmp(*e, "PAPERSIZE", 9)
            || !std::strncmp(*e, "SAL_", 4) || !std::strncmp(*e, "FC_", 3) || !std::strncmp(*e, "PROBE_", 6))
            std::printf("env %s\n", *e);
    std::fflush(stdout);

    LibreOfficeKit *kit = lok_init_2(install, profile);
    if (!kit) { std::fprintf(stderr, "lok_init_2 failed\n"); return 1; }
    readout("after-init");

    // Mutation control only (env PROBE_FORCE_WESTERN_FALLBACK=<bcp47>): overwrite the Western
    // fallback after init, i.e. make the state analysis-1 predicted for a de-DE environment,
    // to show that this load-and-save path can print it in the saved Western slot.
    if (const char *wf = std::getenv("PROBE_FORCE_WESTERN_FALLBACK"); wf && *wf) {
        MsLangId::setConfiguredWesternFallback(LanguageTag::convertToLanguageType(OUString::createFromAscii(wf)));
        readout("after-mutation");
    }

    LibreOfficeKitDocument *doc = nullptr;
    if (options && *options)
        doc = kit->pClass->documentLoadWithOptions(kit, inUrl, options);
    else
        doc = kit->pClass->documentLoad(kit, inUrl);
    if (!doc) {
        char *e = kit->pClass->getError(kit);
        std::fprintf(stderr, "load failed: %s\n", e ? e : "?");
        return 1;
    }
    std::printf("doc type=%d\n", doc->pClass->getDocumentType(doc));
    readout("after-load");

    const char *df = std::getenv("PROBE_DATE_FIELD");
    if (df && !std::strcmp(df, "1")) {
        doc->pClass->initializeForRendering(doc, nullptr);
        doc->pClass->postUnoCommand(doc, ".uno:InsertDateField", nullptr, false);
        sleep(2);
        doc->pClass->postUnoCommand(doc, ".uno:SelectAll", nullptr, false);
        sleep(1);
        char *used = nullptr;
        char *text = doc->pClass->getTextSelection(doc, "text/plain;charset=utf-8", &used);
        std::printf("date-field selection text/plain=\"%s\"\n", text ? text : "(null)");
        std::fflush(stdout);
    }

    std::string outUrl = std::string("file://") + outPath;
    if (!doc->pClass->saveAs(doc, outUrl.c_str(), "odt", nullptr)) {
        char *e = kit->pClass->getError(kit);
        std::fprintf(stderr, "saveAs failed: %s\n", e ? e : "?");
        return 1;
    }
    std::printf("saved %s\n", outPath);
    std::fflush(stdout);
    doc->pClass->destroy(doc);
    kit->pClass->destroy(kit);
    return 0;
}
