#ifndef OXSDK_CALC_CELL_BRIDGE_H
#define OXSDK_CALC_CELL_BRIDGE_H

// Only ods-editor-v1 links this core-internal bridge. Returned UTF-8 JSON is
// malloc-owned by the caller. Calls run on the engine thread under SolarMutex.
// op: 0 read, 1 set formula/input, 2 bold, 3 italic, 4 underline, 5 hit-test.
// For op 5, column/row are document x/y in twips; all other ops use cell indices.
extern "C" char *oxsdk_calc_cell_model(void *lokDocument, int part, int column,
                                      int row, int operation,
                                      const char *text, int textLength,
                                      int enabled);

#endif
