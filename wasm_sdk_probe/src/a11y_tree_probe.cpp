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
#include <comphelper/OAccessible.hxx>

#include <com/sun/star/accessibility/AccessibleRole.hpp>
#include <com/sun/star/accessibility/AccessibleStateType.hpp>
#include <com/sun/star/accessibility/XAccessible.hpp>
#include <com/sun/star/accessibility/XAccessibleContext.hpp>
#include <com/sun/star/accessibility/XAccessibleText.hpp>

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

    // Text length, never the text: this is a shape probe, and the paragraph's
    // text already has its own named contract field.
    css::uno::Reference<css::accessibility::XAccessibleText> xText(
        xContext, css::uno::UNO_QUERY);
    if (xText.is())
    {
        try
        {
            const OUString aText = xText->getText();
            rOut << ",\"textLength\":" << aText.getLength() << ",\"textHead\":\"";
            appendEscaped(rOut, aText.copy(0, std::min<sal_Int32>(24, aText.getLength())));
            rOut << '"';
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
} // namespace

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
