#include "probe_api.h"
#include "probe_engine.hpp"

#include <emscripten/emscripten.h>

#include <cstdlib>
#include <cstring>
#include <string>

namespace
{
bool requireStarted(const char* operation)
{
    if (probe::started())
        return true;

    probe::emitError(operation, "probe_start must be called first");
    return false;
}

bool requireString(const char* value, const char* operation, const char* label)
{
    if (value && value[0] != '\0')
        return true;

    probe::emitError(operation, std::string(label) + " must not be empty");
    return false;
}
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_start(void)
{
    probe::start();
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_open(const char* fileUrl)
{
    if (!requireStarted("open") || !requireString(fileUrl, "open", "file_url"))
        return;
    if (std::strncmp(fileUrl, "file://", 7) != 0)
    {
        probe::emitError("open", "R1 accepts only file:// URLs backed by MEMFS");
        return;
    }
    probe::open(fileUrl);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_paint_tile(
    int xTwips, int yTwips, int widthTwips, int heightTwips,
    int canvasWidthPx, int canvasHeightPx)
{
    if (!requireStarted("tile"))
        return;
    if (xTwips < 0 || yTwips < 0 || widthTwips <= 0 || heightTwips <= 0
        || canvasWidthPx <= 0 || canvasHeightPx <= 0)
    {
        probe::emitError("tile", "tile coordinates and dimensions are invalid");
        return;
    }
    probe::paintTile(xTwips, yTwips, widthTwips, heightTwips,
                     canvasWidthPx, canvasHeightPx);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_click(int xTwips, int yTwips)
{
    if (!requireStarted("click"))
        return;
    if (xTwips < 0 || yTwips < 0)
    {
        probe::emitError("click", "click coordinates must be non-negative");
        return;
    }
    probe::click(xTwips, yTwips);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_insert_text(const char* utf8)
{
    if (!requireStarted("insert") || !requireString(utf8, "insert", "utf8"))
        return;
    probe::insertText(utf8);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_key(int type, int charCode, int keyCode)
{
    if (!requireStarted("key"))
        return;
    if (type < 0 || type > 1 || charCode < 0 || keyCode < 0)
    {
        probe::emitError("key", "key arguments are outside the accepted range");
        return;
    }
    probe::key(type, charCode, keyCode);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_save(const char* format)
{
    if (!requireStarted("save") || !requireString(format, "save", "format"))
        return;
    if (std::strcmp(format, "odt") != 0)
    {
        probe::emitError("save", "R1 supports only the odt output format");
        return;
    }
    probe::save(format);
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_close(void)
{
    if (requireStarted("close"))
        probe::close();
}

extern "C" EMSCRIPTEN_KEEPALIVE void probe_free(void* pointer)
{
    std::free(pointer);
}

int main()
{
    return 0;
}
