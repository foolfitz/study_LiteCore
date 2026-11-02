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
// Old operation values and the frozen v1 identity retain their contracts.
extern "C" char *oxsdk_calc_cell_model(void *lokDocument, int part, int column,
                                      int row, int operation,
                                      const char *text, int textLength,
                                      int enabled);

#endif
