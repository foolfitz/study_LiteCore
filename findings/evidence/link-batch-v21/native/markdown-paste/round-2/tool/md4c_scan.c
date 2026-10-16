/* T3 (link batch v21, spec section 9.3): what the core's own md4c reports for
 * each corpus item, with exactly the flags Writer parses with
 * (libreoffice-26-8/sw/source/filter/md/swmd.cxx:951: MD_DIALECT_GITHUB |
 * MD_FLAG_WIKILINKS). Native model of the engine's planned pre-scan.
 *
 * Build (two files, no make):
 *   gcc -std=c99 -O2 -Wall -I <md4c>/src md4c_scan.c <md4c>/src/md4c.c -o md4c-scan
 * where <md4c> = wasm-lite/build-headless-probe/workdir/UnpackedTarball/md4c.
 *
 * Usage: md4c-scan FILE...   one JSON line per file.
 *
 * Per file it prints:
 *   images, imagesData, imagesNonData  MD_SPAN_IMG count; src starting with
 *                    "data:" (case-sensitive, as the spec words it) or not;
 *   imagesNonDataCI  non-data by a case-INsensitive "data:" test;
 *   srcs             each image's raw src attribute text (entities not resolved);
 *   textCallbacks    text callbacks of any type;
 *   textNonBlank     MD_TEXT_NORMAL/CODE/ENTITY/NULLCHAR callbacks with a byte
 *                    other than ASCII space, \t, \n, \v, \f, \r -- outside images;
 *   textNonBlankInImage  the same, inside an image span (alt text: Writer does
 *                    not insert it as text, mdcallbcks.cxx:278-286);
 *   textNonUnicodeWs the same as textNonBlank but treating Unicode White_Space
 *                    (U+00A0, U+3000, ...) as blank too;
 *   htmlBlocks, htmlText  MD_BLOCK_HTML entered; MD_TEXT_HTML callbacks
 *                    (Writer hands HTML to its HTML import, swmd.cxx:591-603);
 *   blocks           blocks entered, by type, MD_BLOCK_DOC excluded;
 *   parseResult      md_parse's return value.
 */
#include "md4c.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int images, imagesData, imagesNonData, imagesNonDataCI;
    char srcs[8][512];
    int nsrcs;
    int textCallbacks, textNonBlank, textNonBlankInImage, textNonUnicodeWs;
    int htmlBlocks, htmlText;
    int blocks[32];
    int inImage;
} Scan;

static const char *blockName(MD_BLOCKTYPE t) {
    switch (t) {
    case MD_BLOCK_DOC: return "DOC";
    case MD_BLOCK_QUOTE: return "QUOTE";
    case MD_BLOCK_UL: return "UL";
    case MD_BLOCK_OL: return "OL";
    case MD_BLOCK_LI: return "LI";
    case MD_BLOCK_HR: return "HR";
    case MD_BLOCK_H: return "H";
    case MD_BLOCK_CODE: return "CODE";
    case MD_BLOCK_HTML: return "HTML";
    case MD_BLOCK_P: return "P";
    case MD_BLOCK_TABLE: return "TABLE";
    case MD_BLOCK_THEAD: return "THEAD";
    case MD_BLOCK_TBODY: return "TBODY";
    case MD_BLOCK_TR: return "TR";
    case MD_BLOCK_TH: return "TH";
    case MD_BLOCK_TD: return "TD";
    }
    return "?";
}

static int enterBlock(MD_BLOCKTYPE type, void *detail, void *user) {
    Scan *s = (Scan *)user;
    (void)detail;
    if ((int)type >= 0 && (int)type < 32)
        s->blocks[type]++;
    if (type == MD_BLOCK_HTML)
        s->htmlBlocks++;
    return 0;
}

static int leaveBlock(MD_BLOCKTYPE type, void *detail, void *user) {
    (void)type; (void)detail; (void)user;
    return 0;
}

static int enterSpan(MD_SPANTYPE type, void *detail, void *user) {
    Scan *s = (Scan *)user;
    if (type == MD_SPAN_IMG) {
        const MD_SPAN_IMG_DETAIL *d = (const MD_SPAN_IMG_DETAIL *)detail;
        const MD_ATTRIBUTE *src = &d->src;
        int isData = src->size >= 5 && memcmp(src->text, "data:", 5) == 0;
        int isDataCI = src->size >= 5 && (src->text[0] | 0x20) == 'd' && (src->text[1] | 0x20) == 'a' &&
                       (src->text[2] | 0x20) == 't' && (src->text[3] | 0x20) == 'a' && src->text[4] == ':';
        s->images++;
        if (isData) s->imagesData++; else s->imagesNonData++;
        if (!isDataCI) s->imagesNonDataCI++;
        if (s->nsrcs < 8) {
            size_t n = src->size < 511 ? src->size : 511;
            memcpy(s->srcs[s->nsrcs], src->text, n);
            s->srcs[s->nsrcs][n] = 0;
            s->nsrcs++;
        }
        s->inImage++;
    }
    return 0;
}

static int leaveSpan(MD_SPANTYPE type, void *detail, void *user) {
    Scan *s = (Scan *)user;
    (void)detail;
    if (type == MD_SPAN_IMG)
        s->inImage--;
    return 0;
}

/* Unicode White_Space (PropList.txt), as code points. */
static int isUnicodeWs(unsigned cp) {
    return (cp >= 0x09 && cp <= 0x0d) || cp == 0x20 || cp == 0x85 || cp == 0xa0 || cp == 0x1680 ||
           (cp >= 0x2000 && cp <= 0x200a) || cp == 0x2028 || cp == 0x2029 || cp == 0x202f ||
           cp == 0x205f || cp == 0x3000;
}

static int hasNonAsciiBlank(const MD_CHAR *t, MD_SIZE n) {
    for (MD_SIZE i = 0; i < n; i++) {
        unsigned char c = (unsigned char)t[i];
        if (!(c == ' ' || c == '\t' || c == '\n' || c == '\v' || c == '\f' || c == '\r'))
            return 1;
    }
    return 0;
}

static int hasNonUnicodeWs(const MD_CHAR *t, MD_SIZE n) {
    MD_SIZE i = 0;
    while (i < n) {
        unsigned char c = (unsigned char)t[i];
        unsigned cp;
        int len;
        if (c < 0x80) { cp = c; len = 1; }
        else if ((c & 0xe0) == 0xc0 && i + 1 < n) { cp = ((c & 0x1f) << 6) | (t[i + 1] & 0x3f); len = 2; }
        else if ((c & 0xf0) == 0xe0 && i + 2 < n) {
            cp = ((c & 0x0f) << 12) | ((t[i + 1] & 0x3f) << 6) | (t[i + 2] & 0x3f); len = 3;
        } else if ((c & 0xf8) == 0xf0 && i + 3 < n) {
            cp = ((c & 0x07) << 18) | ((t[i + 1] & 0x3f) << 12) | ((t[i + 2] & 0x3f) << 6) | (t[i + 3] & 0x3f);
            len = 4;
        } else { return 1; }
        if (!isUnicodeWs(cp))
            return 1;
        i += len;
    }
    return 0;
}

static int onText(MD_TEXTTYPE type, const MD_CHAR *text, MD_SIZE size, void *user) {
    Scan *s = (Scan *)user;
    s->textCallbacks++;
    if (type == MD_TEXT_HTML) {
        s->htmlText++;
        return 0;
    }
    if (type == MD_TEXT_NORMAL || type == MD_TEXT_CODE || type == MD_TEXT_ENTITY || type == MD_TEXT_NULLCHAR) {
        if (hasNonAsciiBlank(text, size)) {
            if (s->inImage) s->textNonBlankInImage++;
            else s->textNonBlank++;
        }
        if (!s->inImage && hasNonUnicodeWs(text, size))
            s->textNonUnicodeWs++;
    }
    return 0;
}

static void jsonString(const char *v) {
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)v; *p; p++) {
        if (*p == '"' || *p == '\\') printf("\\%c", *p);
        else if (*p < 0x20) printf("\\u%04x", *p);
        else putchar(*p);
    }
    putchar('"');
}

int main(int argc, char **argv) {
    for (int a = 1; a < argc; a++) {
        FILE *f = fopen(argv[a], "rb");
        if (!f) { fprintf(stderr, "cannot open %s\n", argv[a]); return 2; }
        fseek(f, 0, SEEK_END);
        long n = ftell(f);
        fseek(f, 0, SEEK_SET);
        char *buf = malloc(n > 0 ? (size_t)n : 1);
        if (n > 0 && fread(buf, 1, (size_t)n, f) != (size_t)n) { fprintf(stderr, "short read\n"); return 2; }
        fclose(f);
        Scan s;
        memset(&s, 0, sizeof s);
        MD_PARSER parser = {0, MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS, enterBlock, leaveBlock, enterSpan,
                            leaveSpan, onText, NULL, NULL};
        int rc = md_parse(buf, (MD_SIZE)n, &parser, &s);
        const char *name = strrchr(argv[a], '/');
        printf("{\"file\":");
        jsonString(name ? name + 1 : argv[a]);
        printf(",\"bytes\":%ld,\"parseResult\":%d,\"flags\":\"0x%x\",\"images\":%d,\"imagesData\":%d,"
               "\"imagesNonData\":%d,\"imagesNonDataCI\":%d,\"srcs\":[",
               n, rc, (unsigned)(MD_DIALECT_GITHUB | MD_FLAG_WIKILINKS), s.images, s.imagesData,
               s.imagesNonData, s.imagesNonDataCI);
        for (int i = 0; i < s.nsrcs; i++) {
            if (i) putchar(',');
            char cut[90];
            snprintf(cut, sizeof cut, "%.80s%s", s.srcs[i], strlen(s.srcs[i]) > 80 ? "..." : "");
            jsonString(cut);
        }
        printf("],\"textCallbacks\":%d,\"textNonBlank\":%d,\"textNonBlankInImage\":%d,\"textNonUnicodeWs\":%d,"
               "\"htmlBlocks\":%d,\"htmlText\":%d,\"blocks\":{",
               s.textCallbacks, s.textNonBlank, s.textNonBlankInImage, s.textNonUnicodeWs, s.htmlBlocks,
               s.htmlText);
        int first = 1;
        for (int t = 1; t < 32; t++) {
            if (!s.blocks[t]) continue;
            printf("%s\"%s\":%d", first ? "" : ",", blockName((MD_BLOCKTYPE)t), s.blocks[t]);
            first = 0;
        }
        printf("}}\n");
        free(buf);
    }
    return 0;
}
