// Roadmap 3.4: what does the accessibility tree actually look like from inside
// the engine?  DIAGNOSTIC ONLY -- guarded by OXSDK_A11Y_TREE_PROBE and never
// compiled into a product build.
//
// WHY THIS FILE IS SEPARATE, and it is the whole point of its existence:
//
// It is the ONLY translation unit compiled with `-DLIBO_INTERNAL_ONLY`, which
// is how core compiles itself.  Everything else in this engine is a LOK client
// and sees core through the public headers; flipping that define changes what
// those headers present, so it must not be applied to them.  The internal-API
// dependency lives here and nowhere else -- nameable in one place, deletable in
// one place.
//
// And it IS a dependency on internal API: `SfxViewShell::Current()` and
// `vcl::Window::GetAccessible()` carry no cross-release stability promise and
// nothing in LOK's compatibility story covers them.  This file is a BRIDGE.
// The destination is upstream adding role and outline level to LOK's
// focused-paragraph payload (five fields today: content, position, start, end,
// listPrefixLength), at which point this file is deleted rather than
// maintained.
//
// WHAT IT MEASURES, and why it is a probe rather than the feature:
//
// Core's own LOKDocumentFocusListener finds the focused paragraph by
// LISTENING, not by descending, and the state names it knows include
// MANAGES_DESCENDANTS -- a container that manages descendants need not expose
// them as persistent children.  So "descend and look for FOCUSED" is a
// hypothesis, not a plan.  This dumps the shape so the question is answered by
// reading a measurement instead of by reasoning about a header.

#include <sfx2/viewsh.hxx>
#include <vcl/window.hxx>
#include <vcl/outdev.hxx>
#include <vcl/mapmod.hxx>
// `MapUnit` is only FORWARD-DECLARED by the headers above; without this the
// enumerators are invisible and every `MapUnit::MapTwip` is a compile error.
// Same include, same reason, as `tools/f093_native_a11y_geometry_bridge.cpp`.
#include <tools/mapunit.hxx>
#include <tools/gen.hxx>
#include <comphelper/OAccessible.hxx>

#include <com/sun/star/accessibility/AccessibleRole.hpp>
#include <com/sun/star/accessibility/AccessibleStateType.hpp>
#include <com/sun/star/accessibility/XAccessible.hpp>
#include <com/sun/star/accessibility/XAccessibleComponent.hpp>
#include <com/sun/star/accessibility/XAccessibleContext.hpp>
#include <com/sun/star/accessibility/XAccessibleText.hpp>
#include <com/sun/star/accessibility/TextSegment.hpp>
#include <com/sun/star/accessibility/AccessibleTextType.hpp>
#include <com/sun/star/awt/Rectangle.hpp>
#include <com/sun/star/beans/PropertyValue.hpp>

#include <editeng/unoprnms.hxx>

#include <rtl/ustrbuf.hxx>
#include <sal/types.h>

#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>

namespace
{
// Bounded on purpose.  An unbounded walk of a long document's accessibility
// tree is a way to hang the engine while measuring it, and the question here
// is about SHAPE -- roles, states, whether a focused node is findable at all --
// which the first few hundred nodes answer.
constexpr int kMaxDepth = 6;
// RAISED 2026-08-23 after the bound bit the measurement it was protecting.
//
// At 64 children a 133-paragraph document reported exactly 65 nodes, and
// 65 is 1 root + the cap.  Read quickly that says "MANAGES_DESCENDANTS
// materialises only part of the document" -- a conclusion about
// LibreOffice manufactured entirely by a constant in this file.  A bound
// that can be mistaken for the answer has to sit far enough away that
// hitting it is obviously the bound, and it has to be IN the payload so a
// reader can tell the two apart without reading this source.
constexpr sal_Int64 kMaxChildrenPerNode = 4096;
constexpr int kMaxNodes = 4096;
constexpr sal_Int32 kMaxTextHead = 4096;

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

// The three states this question turns on, named rather than dumped as a
// bitmask: FOCUSED is what a descent would look for, MANAGES_DESCENDANTS is
// what would make that descent wrong, and SELECTED is here because Writer's
// caret is a selection of length zero.
void appendStates(std::ostringstream& rOut, sal_Int64 nStates)
{
    namespace State = css::accessibility::AccessibleStateType;
    rOut << ",\"focused\":" << (((nStates & State::FOCUSED) != 0) ? "true" : "false")
         << ",\"managesDescendants\":"
         << (((nStates & State::MANAGES_DESCENDANTS) != 0) ? "true" : "false")
         << ",\"selected\":" << (((nStates & State::SELECTED) != 0) ? "true" : "false");
}

char* duplicate(const std::string& rText)
{
    char* pCopy = static_cast<char*>(std::malloc(rText.size() + 1));
    if (pCopy)
        std::memcpy(pCopy, rText.c_str(), rText.size() + 1);
    return pCopy;
}

int walk(std::ostringstream& rOut,
         const css::uno::Reference<css::accessibility::XAccessibleContext>& xContext,
         int nDepth, int nEmitted, bool& rFirst)
{
    if (!xContext.is() || nDepth > kMaxDepth || nEmitted >= kMaxNodes)
        return nEmitted;

    if (!rFirst)
        rOut << ',';
    rFirst = false;

    sal_Int64 nStates = 0;
    sal_Int16 nRole = -1;
    sal_Int64 nChildren = 0;
    try
    {
        nStates = xContext->getAccessibleStateSet();
        nRole = xContext->getAccessibleRole();
        nChildren = xContext->getAccessibleChildCount();
    }
    catch (const css::uno::Exception&)
    {
        rOut << "{\"depth\":" << nDepth << ",\"error\":\"context threw\"}";
        return nEmitted + 1;
    }

    rOut << "{\"depth\":" << nDepth << ",\"role\":" << nRole
         << ",\"childCount\":" << nChildren;
    appendStates(rOut, nStates);

    // NUMBERING LEVEL AND LIST STATE, asked the way core asks them.
    //
    // `getListPrefixSize()` (sfx2/source/view/viewsh.cxx:554) already queries
    // exactly these two properties off exactly this object, so this is not a
    // new idea about where the data lives -- it is the same query, reported
    // instead of consumed.  WCAG 1.3.1 wants a heading's LEVEL and a list's
    // NESTING, and both are supposed to be here.
    //
    // `attrRunEnd` is reported beside them on purpose: it is the value finding
    // 074 says LOK mistakes for the numbering prefix length, and having all
    // three side by side is what makes that finding checkable from our side
    // rather than only by reading core.
    // Text length, never the text: this is a shape probe, and the paragraph's
    // text already has its own named contract field.
    css::uno::Reference<css::accessibility::XAccessibleText> xText(
        xContext, css::uno::UNO_QUERY);
    if (xText.is())
    {
        try
        {
            const OUString aText = xText->getText();
            // `textHead` was 24 characters while this was purely a SHAPE
            // probe.  Roadmap 3.4's projection needs the paragraph to be
            // readable, so the cap is now 4096 and it travels in the payload
            // (`textHeadCap`) beside the untruncated `textLength` -- a reader
            // can always tell a short paragraph from a clipped one without
            // opening this file.  Same rule the child bound had to learn.
            rOut << ",\"textLength\":" << aText.getLength()
                 << ",\"textHeadCap\":" << kMaxTextHead << ",\"textHead\":\"";
            appendEscaped(rOut, aText.copy(0, std::min<sal_Int32>(kMaxTextHead,
                                                                 aText.getLength())));
            rOut << '"';

            if (aText.getLength() > 0)
            {
                sal_Int16 nLevel = -1;
                bool bCounted = false;
                const css::uno::Sequence<OUString> aWanted{
                    UNO_NAME_NUMBERING_LEVEL, UNO_NAME_NUMBERING};
                const css::uno::Sequence<css::beans::PropertyValue> aAttrs
                    = xText->getCharacterAttributes(0, aWanted);
                for (const auto& rAttr : aAttrs)
                {
                    if (rAttr.Name == UNO_NAME_NUMBERING_LEVEL)
                        rAttr.Value >>= nLevel;
                    else if (rAttr.Name == UNO_NAME_NUMBERING)
                        rAttr.Value >>= bCounted;
                }
                rOut << ",\"numberingLevel\":" << nLevel
                     << ",\"isNumbered\":" << (bCounted ? "true" : "false")
                     << ",\"attrsReturned\":" << aAttrs.getLength();

                const css::accessibility::TextSegment aRun
                    = xText->getTextAtIndex(
                        0, css::accessibility::AccessibleTextType::ATTRIBUTE_RUN);
                rOut << ",\"attrRunEnd\":" << aRun.SegmentEnd;
            }
        }
        catch (const css::uno::Exception&)
        {
            rOut << ",\"textLength\":-1";
        }
    }
    rOut << '}';
    ++nEmitted;

    const sal_Int64 nLimit = std::min<sal_Int64>(nChildren, kMaxChildrenPerNode);
    for (sal_Int64 i = 0; i < nLimit && nEmitted < kMaxNodes; ++i)
    {
        try
        {
            css::uno::Reference<css::accessibility::XAccessible> xChild
                = xContext->getAccessibleChild(i);
            if (!xChild.is())
                continue;
            nEmitted = walk(rOut, xChild->getAccessibleContext(), nDepth + 1,
                            nEmitted, rFirst);
        }
        catch (const css::uno::Exception&)
        {
            // A child that throws is data, not a reason to abandon the walk.
        }
    }
    return nEmitted;
}

// FINDING 093, option B.  Where the paragraph IS, in the space the caret
// already travels in.
//
// WHY THIS EXISTS AT ALL.  The projection built from `documentOutline` was
// sitting at the bottom of the paper, because nothing ever told it where a
// paragraph is; a screen reader bringing a projected node into view therefore
// dragged the desk off the end of the document on every arrow key.  The owner
// found it by eye.  Four candidate fixes were measured against the oracle
// registered in `findings/evidence/093/ORACLE-fix-shape.md`, and on a
// 133-paragraph document only the one that puts each node at ITS OWN
// paragraph's position passes both arms.  This is the engine half of that.
//
// THE CONVERSION, and why it is not a constant.
//
// `XAccessibleComponent::getBounds()` on a Writer paragraph returns OUTPUT
// DEVICE PIXELS -- `SwAccessibleContext::getBoundsImpl` ends in
// `GetMap()->CoreToPixel()`, which is `pWin->LogicToPixel(rect, aMapMode)`
// (`sw/source/core/access/accmap.cxx:2896-2909`).  It is NOT twips and it is
// NOT the 1/100 mm a general UNO convention would suggest; measured on native
// 2026-09-08, the 1/100 mm reading is out by a factor of 26.5
// (`findings/evidence/093/step1-native-geometry/RESULT.md`).
//
// So it has to be converted, and it is converted by asking THE SAME
// OutputDevice to invert its own transform -- never by dividing by a DPI.  The
// native calibration read 96 DPI on the headless svp device of one machine;
// carrying that number across to a wasm artifact is exactly what finding 036
// forbids, and a hard-coded 96 would be right on the native build and silently
// wrong here with nothing downstream able to tell.  `PixelToLogic(rect,
// MapMode(MapUnit::MapTwip))` has no DPI in it: whatever the device's
// resolution is, this is its own inverse of the multiplication that produced
// the pixels.
//
// That form was checked against the exact inverse of `CoreToPixel`
// (`PixelToLogic(rect, dev->GetMapMode())`, the window's own MapMode, origin
// and scale included) on all 114 paragraphs of the native fixture: identical
// on every one, because that device's MapMode is MapTwip at origin (0,0) with
// scale 1.  Both were emitted rather than one, because "they are the same" is
// a measurement and "they must be the same" would have been an assumption.
// The fresh MapMode is the one used here: it depends on no property of the
// device except its resolution, which is the property being inverted.
//
// THE ORIGIN IS DOCUMENT-ABSOLUTE, and that is what makes this usable at all.
// `getBoundsImpl(true)` subtracts the parent's offset only when the parent is
// not the root frame; the accessible tree here is flat -- root plus paragraphs
// at depth 1 -- so that branch is not taken.  Measured, not argued: all 114
// paragraphs reported the walk root as their accessible parent by UNO object
// identity, and the converted `y` ran to 96,240 twips against a 7,440-twip
// window, 12.9 window-heights past the bottom of it.
//
// WHAT IS EMITTED WHEN IT CANNOT BE READ: nothing.  A paragraph whose bounds
// throw, or a view with no OutputDevice, emits no geometry fields rather than
// zeros -- a rectangle at (0,0) is a place, and a projection that believes it
// would put that paragraph at the top of the page and look right while being
// wrong.  Absence is readable; a plausible wrong number is not.
//
// UNMEASURED, AND NAMED HERE RATHER THAN LEFT TO BE DISCOVERED: the outline is
// rebuilt on EVERY state read (`probe_engine.cpp:1177-1182` records that as a
// measured choice), so this adds one `getBounds()` per paragraph per read --
// 133 on the long fixture.  What that costs has never been measured, on either
// build.  Step 1 measured coordinates, not time.
void appendParagraphGeometry(
    std::ostringstream& rOut,
    const css::uno::Reference<css::accessibility::XAccessibleContext>& xCtx,
    const OutputDevice* pDev)
{
    if (!pDev)
        return;
    try
    {
        css::uno::Reference<css::accessibility::XAccessibleComponent> xComp(
            xCtx, css::uno::UNO_QUERY);
        if (!xComp.is())
            return;
        const css::awt::Rectangle aBounds = xComp->getBounds();
        const tools::Rectangle aTwips = pDev->PixelToLogic(
            tools::Rectangle(Point(aBounds.X, aBounds.Y),
                             Size(aBounds.Width, aBounds.Height)),
            MapMode(MapUnit::MapTwip));
        rOut << ",\"x\":" << aTwips.Left() << ",\"y\":" << aTwips.Top()
             << ",\"width\":" << aTwips.GetWidth()
             << ",\"height\":" << aTwips.GetHeight();
    }
    catch (const css::uno::Exception&)
    {
        // Data, not a reason to abandon the paragraph: the row still carries
        // its role, level and text, and the projection can still speak it.
    }
}
} // namespace

// THE PRODUCT SHAPE, beside the diagnostic one on purpose.
//
// `oxsdk_a11y_tree_snapshot()` below dumps what the tree IS -- depths, child
// counts, state bits, attribute-run ends. That is a probe's output and it must
// not become a product surface: E1-B's ban is on promoting diagnostic
// internals, and every one of those fields is exactly that.
//
// This emits what a projection NEEDS and nothing else: role as a product word,
// level, list membership, focus, text. The vocabulary is the product's
// ("heading"/"listItem"/"paragraph"), not AccessibleRole integers, so a host
// never has to know that 26 means heading.
//
// Everything it reads was measured before it was written
// (findings/evidence/aria-projection/TREE-SHAPE.md): role is an enum rather
// than the localised style name finding 031 is about, level is
// NumberingLevel + 1 across seven outline levels including a gap, and list
// membership is `isNumbered` read AFTER role because a heading reports
// numbered too.
extern "C" char* oxsdk_a11y_document_outline()
{
    std::ostringstream aOut;
    try
    {
        SfxViewShell* pShell = SfxViewShell::Current();
        vcl::Window* pWindow = pShell ? pShell->GetWindow() : nullptr;
        // FINDING 093.  The device the bounds have to be inverted on, taken
        // from the SAME window the accessible tree is taken from -- asking a
        // different OutputDevice to undo this one's transform is how a
        // conversion becomes plausible and wrong.  `nullptr` is tolerated:
        // `appendParagraphGeometry` then emits no geometry, and the page has a
        // declared state for that.
        const OutputDevice* pDev = pWindow ? pWindow->GetOutDev() : nullptr;
        rtl::Reference<comphelper::OAccessible> xAcc
            = pWindow ? pWindow->GetAccessible() : nullptr;
        if (!xAcc.is())
        {
            // Absent, not empty.  A host that cannot tell "no accessibility
            // here" from "a document with no paragraphs" would announce a
            // blank document, which is the failure the region above it exists
            // to prevent.
            return duplicate("{\"unavailable\":\"no-accessible\"}");
        }

        css::uno::Reference<css::accessibility::XAccessibleContext> xRoot
            = xAcc->getAccessibleContext();
        const sal_Int64 nChildren = xRoot->getAccessibleChildCount();
        const sal_Int64 nLimit = std::min<sal_Int64>(nChildren, kMaxChildrenPerNode);

        aOut << "{\"paragraphCount\":" << nChildren
             << ",\"cap\":" << kMaxChildrenPerNode
             << ",\"textCap\":" << kMaxTextHead
             << ",\"paragraphs\":[";
        bool bFirst = true;
        for (sal_Int64 i = 0; i < nLimit; ++i)
        {
            css::uno::Reference<css::accessibility::XAccessible> xChild
                = xRoot->getAccessibleChild(i);
            if (!xChild.is())
                continue;
            css::uno::Reference<css::accessibility::XAccessibleContext> xCtx
                = xChild->getAccessibleContext();
            if (!xCtx.is())
                continue;

            const sal_Int16 nRole = xCtx->getAccessibleRole();
            const sal_Int64 nStates = xCtx->getAccessibleStateSet();
            const bool bFocused
                = (nStates & css::accessibility::AccessibleStateType::FOCUSED) != 0;

            OUString aText;
            sal_Int16 nLevel = -1;
            bool bCounted = false;
            css::uno::Reference<css::accessibility::XAccessibleText> xText(
                xCtx, css::uno::UNO_QUERY);
            if (xText.is())
            {
                aText = xText->getText();
                if (aText.getLength() > 0)
                {
                    const css::uno::Sequence<OUString> aWanted{
                        UNO_NAME_NUMBERING_LEVEL, UNO_NAME_NUMBERING};
                    for (const auto& rAttr : xText->getCharacterAttributes(0, aWanted))
                    {
                        if (rAttr.Name == UNO_NAME_NUMBERING_LEVEL)
                            rAttr.Value >>= nLevel;
                        else if (rAttr.Name == UNO_NAME_NUMBERING)
                            rAttr.Value >>= bCounted;
                    }
                }
            }

            const bool bHeading
                = nRole == css::accessibility::AccessibleRole::HEADING;
            // Order matters and it is measured: a heading also reports
            // `numbered`, outline numbering being numbering, so role is asked
            // first and list membership only of what is left.
            const bool bListItem = !bHeading && bCounted;

            if (!bFirst)
                aOut << ',';
            bFirst = false;
            aOut << "{\"role\":\""
                 << (bHeading ? "heading" : bListItem ? "listItem" : "paragraph")
                 << "\",\"level\":" << (nLevel + 1)
                 << ",\"focused\":" << (bFocused ? "true" : "false")
                 << ",\"textLength\":" << aText.getLength();
            // FINDING 093, and it is deliberately here rather than beside the
            // diagnostic tree below: this is the PRODUCT shape, and a
            // projection that knows what a paragraph says but not where it is
            // is the defect this fixes.
            appendParagraphGeometry(aOut, xCtx, pDev);
            aOut << ",\"text\":\"";
            appendEscaped(aOut, aText.copy(0, std::min<sal_Int32>(
                                    kMaxTextHead, aText.getLength())));
            aOut << "\"}";
        }
        aOut << "]}";
    }
    catch (const css::uno::Exception&)
    {
        return duplicate("{\"unavailable\":\"uno-exception\"}");
    }
    return duplicate(aOut.str());
}

extern "C" char* oxsdk_a11y_tree_snapshot()
{
    std::ostringstream aOut;
    aOut << '{';
    try
    {
        SfxViewShell* pShell = SfxViewShell::Current();
        if (!pShell)
        {
            aOut << "\"unavailable\":\"no-current-view-shell\"}";
        }
        else
        {
            vcl::Window* pWindow = pShell->GetWindow();
            if (!pWindow)
            {
                aOut << "\"unavailable\":\"view-shell-has-no-window\"}";
            }
            else
            {
                rtl::Reference<comphelper::OAccessible> xAcc = pWindow->GetAccessible();
                if (!xAcc.is())
                {
                    // The honest reading on a core built with
                    // ENABLE_WASM_STRIP_ACCESSIBILITY: CreateAccessible()
                    // returns {} and there is no tree at all.
                    aOut << "\"unavailable\":\"window-has-no-accessible\"}";
                }
                else
                {
                    aOut << "\"nodes\":[";
                    bool bFirst = true;
                    const int nEmitted
                        = walk(aOut, xAcc->getAccessibleContext(), 0, 0, bFirst);
                    aOut << "],\"emitted\":" << nEmitted
                         << ",\"maxNodes\":" << kMaxNodes
                         << ",\"maxChildrenPerNode\":" << kMaxChildrenPerNode
                         << ",\"maxDepth\":" << kMaxDepth << '}';
                }
            }
        }
    }
    catch (const css::uno::Exception&)
    {
        aOut.str("");
        aOut << "{\"unavailable\":\"uno-exception\"}";
    }

    const std::string aResult = aOut.str();
    char* pCopy = static_cast<char*>(std::malloc(aResult.size() + 1));
    if (pCopy)
        std::memcpy(pCopy, aResult.c_str(), aResult.size() + 1);
    return pCopy;
}
