// Finding 093, option B, step 1 -- the core-internal half of the calibration
// probe.  Native only.  Nothing here describes the wasm artifact.
//
// WHY THIS FILE IS SEPARATE, and it is the whole point of its existence:
//
// It is the only translation unit of this probe compiled with
// `-DLIBO_INTERNAL_ONLY`, which is how core compiles itself.  The other half
// (`f093_native_a11y_geometry.cpp`) is a LOK client and sees core through the
// public headers; flipping that define changes what those headers present, so
// it must not be applied to them.  Same split, same reason, as
// `src/a11y_tree_probe.cpp` in the engine.
//
// WHAT IT MEASURES:
//
// `handoff/RUNBOOK-operator-093-engine-geometry.md` section 2 -- the whole
// coordinate space -- is READ FROM SOURCE, not measured.  Three things are
// unknown: the unit `XAccessibleComponent::getBounds()` returns, the origin it
// is relative to, and whether converting it to twips lines up with the caret
// rectangle LOK already hands the page.  This dumps what is needed to answer
// all three from a measurement.
//
// It reports RATHER THAN DECIDES.  Every judgement lives in
// `tools/analyze_f093_native_geometry.py`, against the tolerances registered in
// `findings/evidence/093/step1-native-geometry/ACCEPTANCE.md` (commit
// `bcb7caf4`, written before this file existed).
//
// TWO CONVERSIONS ARE EMITTED, ON PURPOSE:
//
//   * `twipsFresh` -- `PixelToLogic(rect, MapMode(MapUnit::MapTwip))`, the form
//     the runbook proposes.  A fresh MapMode: origin (0,0), scale 1:1.
//   * `twipsDevice` -- `PixelToLogic(rect, dev->GetMapMode())`, the exact
//     inverse of what `SwAccessibleMap::CoreToPixel` did on the way out
//     (`sw/source/core/access/accmap.cxx:2896-2909` passes the window's OWN
//     MapMode, origin and scale included).
//
// If the device's MapMode is twips at origin (0,0) with scale 1:1 the two are
// the same number and saying so is a measurement.  If they differ, the
// difference is the answer to "which conversion does the product need", and
// emitting only one of them would have hidden it.

#include <sfx2/viewsh.hxx>
#include <vcl/window.hxx>
#include <vcl/outdev.hxx>
#include <vcl/mapmod.hxx>
// `MapUnit` is only FORWARD-DECLARED by the headers above; without this the
// enumerators are invisible and every `MapUnit::MapTwip` is a compile error.
#include <tools/mapunit.hxx>
#include <vcl/svapp.hxx>
#include <tools/gen.hxx>
#include <tools/fract.hxx>
#include <comphelper/OAccessible.hxx>

#include <com/sun/star/accessibility/AccessibleStateType.hpp>
#include <com/sun/star/accessibility/XAccessible.hpp>
#include <com/sun/star/accessibility/XAccessibleComponent.hpp>
#include <com/sun/star/accessibility/XAccessibleContext.hpp>
#include <com/sun/star/accessibility/XAccessibleText.hpp>
#include <com/sun/star/awt/Point.hpp>
#include <com/sun/star/awt/Rectangle.hpp>
#include <com/sun/star/uno/XInterface.hpp>

#include <rtl/ustring.hxx>
#include <sal/types.h>

#include <algorithm>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>

namespace
{
// Enough of the paragraph to carry the `LD-Pnn-Lmm` marker the run navigates
// by, and no more.  Pairing is by marker and by the FOCUSED state; the text is
// here so the judge can check the pairing rather than trust it.
constexpr sal_Int32 kTextHead = 40;
constexpr sal_Int64 kMaxParagraphs = 4096;

void appendEscaped(std::ostringstream& rOut, const OUString& rText)
{
    const OString aUtf8 = rText.toUtf8();
    for (sal_Int32 i = 0; i < aUtf8.getLength(); ++i)
    {
        const char c = aUtf8[i];
        switch (c)
        {
            case '"': rOut << "\\\""; break;
            case '\\': rOut << "\\\\"; break;
            case '\n': rOut << "\\n"; break;
            case '\r': rOut << "\\r"; break;
            case '\t': rOut << "\\t"; break;
            default:
                if (static_cast<unsigned char>(c) < 0x20)
                    rOut << ' ';
                else
                    rOut << c;
        }
    }
}

char* duplicate(const std::string& rText)
{
    char* pCopy = static_cast<char*>(std::malloc(rText.size() + 1));
    if (pCopy)
        std::memcpy(pCopy, rText.c_str(), rText.size() + 1);
    return pCopy;
}

const char* mapUnitName(MapUnit eUnit)
{
    switch (eUnit)
    {
        case MapUnit::Map100thMM: return "Map100thMM";
        case MapUnit::Map10thMM: return "Map10thMM";
        case MapUnit::MapMM: return "MapMM";
        case MapUnit::MapCM: return "MapCM";
        case MapUnit::Map1000thInch: return "Map1000thInch";
        case MapUnit::Map100thInch: return "Map100thInch";
        case MapUnit::Map10thInch: return "Map10thInch";
        case MapUnit::MapInch: return "MapInch";
        case MapUnit::MapPoint: return "MapPoint";
        case MapUnit::MapTwip: return "MapTwip";
        case MapUnit::MapPixel: return "MapPixel";
        case MapUnit::MapSysFont: return "MapSysFont";
        case MapUnit::MapAppFont: return "MapAppFont";
        case MapUnit::MapRelative: return "MapRelative";
        default: return "unknown";
    }
}

void appendRect(std::ostringstream& rOut, const char* pName, const tools::Rectangle& rRect)
{
    rOut << "\"" << pName << "\":{\"x\":" << rRect.Left() << ",\"y\":" << rRect.Top()
         << ",\"w\":" << rRect.GetWidth() << ",\"h\":" << rRect.GetHeight() << "}";
}

// The identity comparison O-1 turns on.  Two `Reference`s to the same object
// reached through different interfaces are not pointer-equal until both are
// narrowed to XInterface, which is what UNO defines identity as.
void* unoIdentity(const css::uno::Reference<css::uno::XInterface>& x)
{
    if (!x.is())
        return nullptr;
    css::uno::Reference<css::uno::XInterface> xId(x, css::uno::UNO_QUERY);
    return xId.get();
}

// The text a paragraph reports, or an empty string if it cannot be asked.
// Separated out because the marker cross-check needs it BEFORE the decision to
// emit, and the emitted row needs it again.
OUString paragraphText(const css::uno::Reference<css::accessibility::XAccessibleContext>& xCtx)
{
    try
    {
        css::uno::Reference<css::accessibility::XAccessibleText> xText(xCtx,
                                                                      css::uno::UNO_QUERY);
        if (xText.is())
            return xText->getText();
    }
    catch (const css::uno::Exception&)
    {
    }
    return OUString();
}

void emitParagraph(std::ostringstream& rOut, sal_Int64 nIndex,
                   const css::uno::Reference<css::accessibility::XAccessible>& xChild,
                   const OutputDevice* pDev, void* pWalkRootIdentity,
                   bool bMarkerMatch)
{
    rOut << "{\"index\":" << nIndex << ",\"markerMatch\":"
         << (bMarkerMatch ? "true" : "false");

    css::uno::Reference<css::accessibility::XAccessibleContext> xCtx;
    try
    {
        xCtx = xChild->getAccessibleContext();
    }
    catch (const css::uno::Exception&)
    {
    }
    if (!xCtx.is())
    {
        rOut << ",\"error\":\"no-context\"}";
        return;
    }

    try
    {
        const sal_Int64 nStates = xCtx->getAccessibleStateSet();
        rOut << ",\"role\":" << xCtx->getAccessibleRole() << ",\"focused\":"
             << (((nStates & css::accessibility::AccessibleStateType::FOCUSED) != 0)
                     ? "true" : "false");
    }
    catch (const css::uno::Exception&)
    {
        rOut << ",\"role\":-1,\"focused\":false";
    }

    // O-1: is this paragraph's accessible parent the very context the walk
    // started from?  The runbook ARGUES it is (flat tree, shared GetParent()).
    // Reported per row so the argument is not inherited.
    try
    {
        css::uno::Reference<css::accessibility::XAccessible> xParent
            = xCtx->getAccessibleParent();
        void* pParentIdentity = nullptr;
        if (xParent.is())
        {
            css::uno::Reference<css::accessibility::XAccessibleContext> xParentCtx
                = xParent->getAccessibleContext();
            pParentIdentity = unoIdentity(
                css::uno::Reference<css::uno::XInterface>(xParentCtx, css::uno::UNO_QUERY));
        }
        rOut << ",\"parentIsWalkRoot\":"
             << ((pParentIdentity != nullptr && pParentIdentity == pWalkRootIdentity)
                     ? "true" : "false")
             << ",\"hasParent\":" << (xParent.is() ? "true" : "false");
    }
    catch (const css::uno::Exception&)
    {
        rOut << ",\"parentIsWalkRoot\":false,\"hasParent\":false";
    }

    {
        const OUString aText = paragraphText(xCtx);
        rOut << ",\"textLength\":" << aText.getLength() << ",\"textHead\":\"";
        appendEscaped(rOut, aText.copy(0, std::min<sal_Int32>(kTextHead, aText.getLength())));
        rOut << "\"";
    }

    // The call the whole of option B rests on.
    css::uno::Reference<css::accessibility::XAccessibleComponent> xComp(xCtx,
                                                                       css::uno::UNO_QUERY);
    rOut << ",\"hasComponent\":" << (xComp.is() ? "true" : "false");
    if (!xComp.is())
    {
        rOut << '}';
        return;
    }

    try
    {
        const css::awt::Rectangle aBounds = xComp->getBounds();
        const tools::Rectangle aRaw(Point(aBounds.X, aBounds.Y),
                                    Size(aBounds.Width, aBounds.Height));
        rOut << ',';
        appendRect(rOut, "raw", aRaw);
        rOut << ',';
        appendRect(rOut, "twipsFresh",
                   pDev->PixelToLogic(aRaw, MapMode(MapUnit::MapTwip)));
        rOut << ',';
        appendRect(rOut, "twipsDevice", pDev->PixelToLogic(aRaw, pDev->GetMapMode()));
        rOut << ',';
        // The third unit hypothesis, converted the same way, so "it is not
        // 1/100 mm" is a number in the capture rather than an assertion in a
        // report.
        appendRect(rOut, "hundredthMM",
                   pDev->PixelToLogic(aRaw, MapMode(MapUnit::Map100thMM)));

        const css::awt::Point aScreen = xComp->getLocationOnScreen();
        rOut << ",\"screen\":{\"x\":" << aScreen.X << ",\"y\":" << aScreen.Y << "}";
    }
    catch (const css::uno::Exception&)
    {
        rOut << ",\"error\":\"bounds-threw\"";
    }

    rOut << '}';
}
} // namespace

// bAllParagraphs == 0 -> device block plus the paragraphs that are FOCUSED or
//                        whose text contains `pMarker` (either qualifies; each
//                        row says which, so the acceptance's cross-check is a
//                        comparison in the capture rather than a claim in a
//                        report).
// bAllParagraphs != 0 -> device block plus every child of the walk root.
//
// `pMarker` may be null.  Caller frees the result.
extern "C" char* f093_geometry_snapshot(int bAllParagraphs, const char* pMarker)
{
    std::ostringstream aOut;
    try
    {
        SolarMutexGuard aGuard;

        SfxViewShell* pShell = SfxViewShell::Current();
        vcl::Window* pWindow = pShell ? pShell->GetWindow() : nullptr;
        if (!pWindow)
            return duplicate("{\"available\":false,\"reason\":\"no-window\"}");
        const OutputDevice* pDev = pWindow->GetOutDev();
        if (!pDev)
            return duplicate("{\"available\":false,\"reason\":\"no-outdev\"}");

        rtl::Reference<comphelper::OAccessible> xAcc = pWindow->GetAccessible();
        if (!xAcc.is())
            return duplicate("{\"available\":false,\"reason\":\"no-accessible\"}");

        aOut << "{\"available\":true,\"device\":{";
        const MapMode& rMode = pDev->GetMapMode();
        aOut << "\"mapUnit\":" << static_cast<int>(rMode.GetMapUnit())
             << ",\"mapUnitName\":\"" << mapUnitName(rMode.GetMapUnit())
             << "\",\"originX\":" << rMode.GetOrigin().X()
             << ",\"originY\":" << rMode.GetOrigin().Y()
             << ",\"scaleX\":" << rMode.GetScaleX()
             << ",\"scaleY\":" << rMode.GetScaleY();

        // Three independent reads of the DPI.  The acceptance says that if they
        // disagree, the disagreement is the answer and no single DPI is named.
        aOut << ",\"dpiX\":" << pDev->GetDPIX() << ",\"dpiY\":" << pDev->GetDPIY()
             << ",\"dpiScalePercentage\":" << pDev->GetDPIScalePercentage();
        const Size aInchPx
            = pDev->LogicToPixel(Size(1440, 1440), MapMode(MapUnit::MapTwip));
        aOut << ",\"pxPerInchX\":" << aInchPx.Width()
             << ",\"pxPerInchY\":" << aInchPx.Height();

        const Size aOutPx = pDev->GetOutputSizePixel();
        const Size aOutTwips = pDev->PixelToLogic(aOutPx, MapMode(MapUnit::MapTwip));
        aOut << ",\"outputWidthPx\":" << aOutPx.Width()
             << ",\"outputHeightPx\":" << aOutPx.Height()
             << ",\"outputWidthTwips\":" << aOutTwips.Width()
             << ",\"outputHeightTwips\":" << aOutTwips.Height() << "}";

        css::uno::Reference<css::accessibility::XAccessibleContext> xRoot
            = xAcc->getAccessibleContext();
        if (!xRoot.is())
        {
            aOut << ",\"reason\":\"no-root-context\"}";
            return duplicate(aOut.str());
        }
        void* pWalkRootIdentity = unoIdentity(
            css::uno::Reference<css::uno::XInterface>(xRoot, css::uno::UNO_QUERY));

        // The root's own bounds, beside the paragraphs'.  If the paragraphs
        // were parent-relative the root would be the frame they are relative
        // to, and its rectangle is the only way to see that from the capture.
        css::uno::Reference<css::accessibility::XAccessibleComponent> xRootComp(
            xRoot, css::uno::UNO_QUERY);
        aOut << ",\"root\":{\"role\":" << xRoot->getAccessibleRole()
             << ",\"hasComponent\":" << (xRootComp.is() ? "true" : "false");
        if (xRootComp.is())
        {
            const css::awt::Rectangle aRB = xRootComp->getBounds();
            const tools::Rectangle aRaw(Point(aRB.X, aRB.Y), Size(aRB.Width, aRB.Height));
            aOut << ',';
            appendRect(aOut, "raw", aRaw);
            aOut << ',';
            appendRect(aOut, "twipsFresh",
                       pDev->PixelToLogic(aRaw, MapMode(MapUnit::MapTwip)));
            const css::awt::Point aScreen = xRootComp->getLocationOnScreen();
            aOut << ",\"screen\":{\"x\":" << aScreen.X << ",\"y\":" << aScreen.Y << "}";
        }
        aOut << "}";

        const sal_Int64 nChildren = xRoot->getAccessibleChildCount();
        aOut << ",\"paragraphCount\":" << nChildren << ",\"cap\":" << kMaxParagraphs
             << ",\"all\":" << (bAllParagraphs ? "true" : "false") << ",\"marker\":\"";
        if (pMarker)
            appendEscaped(aOut, OUString::createFromAscii(pMarker));
        aOut << "\",\"paragraphs\":[";
        const sal_Int64 nLimit = std::min<sal_Int64>(nChildren, kMaxParagraphs);
        bool bFirst = true;
        for (sal_Int64 i = 0; i < nLimit; ++i)
        {
            css::uno::Reference<css::accessibility::XAccessible> xChild;
            try
            {
                xChild = xRoot->getAccessibleChild(i);
            }
            catch (const css::uno::Exception&)
            {
                continue;
            }
            if (!xChild.is())
                continue;

            bool bMarkerMatch = false;
            if (!bAllParagraphs)
            {
                // Selective mode still has to ASK every child: the focused one
                // is found by its state, and the marker one by its text.
                // Neither is an index this probe could have guessed, and
                // neither is a coordinate -- which is the point.
                bool bFocused = false;
                try
                {
                    css::uno::Reference<css::accessibility::XAccessibleContext> xCtx
                        = xChild->getAccessibleContext();
                    if (xCtx.is())
                    {
                        bFocused = (xCtx->getAccessibleStateSet()
                                    & css::accessibility::AccessibleStateType::FOCUSED)
                                   != 0;
                        if (pMarker && *pMarker)
                            bMarkerMatch = paragraphText(xCtx).indexOf(
                                               OUString::createFromAscii(pMarker))
                                           >= 0;
                    }
                }
                catch (const css::uno::Exception&)
                {
                }
                if (!bFocused && !bMarkerMatch)
                    continue;
            }

            if (!bFirst)
                aOut << ',';
            bFirst = false;
            emitParagraph(aOut, i, xChild, pDev, pWalkRootIdentity, bMarkerMatch);
        }
        aOut << "]}";
    }
    catch (const css::uno::Exception&)
    {
        return duplicate("{\"available\":false,\"reason\":\"uno-exception\"}");
    }
    return duplicate(aOut.str());
}
