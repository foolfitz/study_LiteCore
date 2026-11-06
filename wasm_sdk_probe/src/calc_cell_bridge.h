#ifndef OXSDK_CALC_CELL_BRIDGE_H
#define OXSDK_CALC_CELL_BRIDGE_H

// Calc editor profiles link this core-internal bridge. Returned UTF-8 JSON is
// malloc-owned by the caller. Calls run on the engine thread under SolarMutex.
// op: 0 read, 1 set formula/input, 2 bold, 3 italic, 4 underline, 5 hit-test.
// For op 5, column/row are document x/y in twips; all other ops use cell indices.
// OXSDK_ODS_RANGE appends 6 range read and 7/8/9 range bold/italic/underline.
// These receive JSON {endColumn,endRow} in text and return a range snapshot.
// OXSDK_ODS_STYLE appends 10 text colour, 11 background colour and 12 horizontal
// alignment, range only: JSON {endColumn,endRow,value}, where value is "#rrggbb"
// or "auto" (10), "#rrggbb" or "none" (11), standard|left|center|right|block (12).
// Snapshots then carry textColor, backColor and horizontalAlign.
// OXSDK_ODS_HEADERS (SPEC-P-calc-headers) appends 13, read-only: JSON {x,y,width,height}
// in twips; returns maxColumns, maxRows and the visible columns/rows as
// {index,label,startPx,endPx,hidden}, without selecting a cell.  With it, whole
// columns, rows and the sheet pass the range cell limit and the merge boundary.
// OXSDK_ODS_STRUCTURE (SPEC-P-calc-structure, requires HEADERS) appends 14: JSON
// {axis:"rows"|"columns",action:"insert"|"delete",index,count}; whole rows or
// columns through UNO insertByIndex/removeByIndex; STRUCTURE_REFUSED when the core refuses.
// OXSDK_ODS_COPY (SPEC-P-calc-copy, requires STRUCTURE) appends 15, read-only: JSON
// {endColumn,endRow}; returns plainText, the core's own copy text for the range
// (getTextSelection after selecting it), and the marked range; the selection is restored.
// OXSDK_ODS_COPY_HTML (SPEC-P-calc-copy append 2, requires COPY) adds htmlText to 15's reply:
// the core's own text/html for the same selection, absent when the core gives none.
// OXSDK_ODS_ZOOM (SPEC-P-calc-zoom, requires COPY) appends 16, read-only for the document:
// JSON {tileTwips} in {7680,5120,3840,3072,2560,1920} (50..200%); every later operation sets
// the view's client zoom to 256 px per tileTwips (3840 before, and without the define);
// replies with the document size in twips at that zoom.
// Old operation values and the frozen v1 identity retain their contracts.
extern "C" char *oxsdk_calc_cell_model(void *lokDocument, int part, int column,
                                      int row, int operation,
                                      const char *text, int textLength,
                                      int enabled);

#endif
