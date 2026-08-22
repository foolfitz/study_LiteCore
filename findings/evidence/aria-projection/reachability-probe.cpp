// Reachability probe for roadmap 3.4 option (i): can our engine get to the
// accessibility object itself, past LOK's five-field payload?
//
// Compile only.  If the headers are unusable from the engine's own flags, (i)
// is dead before any design work; if they compile, the next question is
// whether the symbols link.
#include <sfx2/viewsh.hxx>
#include <com/sun/star/accessibility/XAccessible.hpp>
#include <com/sun/star/accessibility/XAccessibleContext.hpp>
#include <com/sun/star/accessibility/AccessibleRole.hpp>
#include <vcl/window.hxx>
#include <comphelper/OAccessible.hxx>

extern "C" int oxsdk_reach_probe();

int oxsdk_reach_probe()
{
    SfxViewShell *pShell = SfxViewShell::Current();
    if (!pShell)
        return -1;
    vcl::Window *pWindow = pShell->GetWindow();
    if (!pWindow)
        return -2;
    rtl::Reference<comphelper::OAccessible> xAcc = pWindow->GetAccessible();
    if (!xAcc.is())
        return -3;
    css::uno::Reference<css::accessibility::XAccessibleContext> xContext =
        xAcc->getAccessibleContext();
    if (!xContext.is())
        return -4;
    return static_cast<int>(xContext->getAccessibleRole());
}
