"""Model of Writer's reported width under PaintTile (PostItMgr::GetSidebarWidth pixel round trip)."""
import math, sys
PAGE = 11906; BORDER = 284; F = 3.0
def rnd(x): return math.floor(x + 0.5)
def engine(cw, W):
    scale = cw / W * 15.0                      # SwViewShell::PaintTile scaleX (px->twip: 1 px = 15 twip)
    nZoom = int(scale * 100)                   # sal_uInt16 truncation in GetSidebarWidth
    px = int(nZoom * F)                        # tools::ULong(nZoom * DisplayWidthFactor)
    sidebar = rnd(px * W / cw)                 # PixelToLogic through the tile's MapMode
    border = rnd(2 * W / cw)                   # GetSidebarBorderWidth: 2 px
    return PAGE + 2 * BORDER + sidebar + border
def page_cw(W, z, avail=900):
    return min(avail, 900) if z is None else rnd(W / 15 * z / 100)
def run(W, z, avail=900, limit=12):
    seen = []
    for i in range(limit):
        cw = page_cw(W, z, avail)
        W2 = engine(cw, W)
        seen.append((cw, W, W2))
        if W2 == W: return W, seen, 'settled after %d changes' % (len(seen) - 1)
        W = W2
    return W, seen, 'NO FIXED POINT in %d' % limit
W = 17004
for z in (None, 100, 125, 150, 200):
    W, seen, verdict = run(W, z)
    print('level', z or 'fit', verdict, 'cw', sorted({s[0] for s in seen}), 'W', sorted({s[2] for s in seen}))
print('--- fit at narrow desks (cssWidth = available):')
for avail in range(700, 760):
    Wf, seen, verdict = run(17004, None, avail)
    if 'NO' in verdict: print('  available', avail, 'label', rnd(avail * 1500 / 17004), '%', verdict, 'W', sorted({s[2] for s in seen}))
