// SPEC-P-calc-undo 4.4 (NU-2, NU-3): calc_cell_native.cpp (SPEC-M4-cell-editing-v1, not edited) plus a
// document callback and one action, "uno-wait": post the command with notification and wait for its
// LOK_CALLBACK_UNO_COMMAND_RESULT, reporting the payload or that none came.  Observations, not verdicts.
// 2026-11-07, SPEC-P-calc-copy append 2: one more action, "paste": LOK paste(mimeType, data) at the cell
// cursor, which puts the data on the view's clipboard and dispatches .uno:Paste (init.cxx doc_paste).
// SPEC-P-calc-zoom: "paint": LOK paintTile into a width x height buffer for the tile at x, y of
// tileWidth x tileHeight twips, written raw (the core's BGRA) to "file".
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
#include "../src/calc_cell_bridge.h"
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <vector>
#include <sstream>
#include <thread>
#include <chrono>
#include <condition_variable>
#include <mutex>
#include <string>

namespace {
std::mutex gMutex;
std::condition_variable gCond;
std::string gResult;
bool gHaveResult = false;

void onCallback(int type, const char *payload, void *) {
  if (type != LOK_CALLBACK_UNO_COMMAND_RESULT) return;
  std::lock_guard<std::mutex> lock(gMutex);
  gResult = payload ? payload : "";
  gHaveResult = true;
  gCond.notify_all();
}
}

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  auto *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 3;
  auto *doc = kit->pClass->documentLoad(kit, argv[3]);
  if (!doc) return 4;
  doc->pClass->initializeForRendering(doc, nullptr);
  doc->pClass->registerCallback(doc, onCallback, nullptr);
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  std::string line;
  while (std::getline(std::cin, line)) {
    boost::property_tree::ptree request;
    std::istringstream input(line);
    boost::property_tree::read_json(input, request);
    if (request.get<std::string>("action", "") == "command-values") {
      char *raw = doc->pClass->getCommandValues(doc, request.get<std::string>("command").c_str());
      std::cout << (raw ? raw : "null") << std::endl;
      std::free(raw);
      continue;
    }
    if (request.get<std::string>("action", "") == "uno-wait") {
      const auto command = request.get<std::string>("command");
      const int timeoutMs = request.get<int>("timeoutMs", 3000);
      {
        std::lock_guard<std::mutex> lock(gMutex);
        gHaveResult = false;
        gResult.clear();
      }
      const auto started = std::chrono::steady_clock::now();
      doc->pClass->postUnoCommand(doc, command.c_str(), nullptr, true);
      std::unique_lock<std::mutex> lock(gMutex);
      const bool came = gCond.wait_for(lock, std::chrono::milliseconds(timeoutMs), [] { return gHaveResult; });
      const auto waited = std::chrono::duration_cast<std::chrono::milliseconds>(
          std::chrono::steady_clock::now() - started).count();
      std::cout << "{\"resultCame\":" << (came ? "true" : "false") << ",\"waitedMs\":" << waited;
      if (came) std::cout << ",\"result\":" << (gResult.empty() ? "null" : gResult);
      std::cout << "}" << std::endl;
      continue;
    }
    if (request.get<std::string>("action", "") == "uno") {
      doc->pClass->postUnoCommand(doc, request.get<std::string>("command").c_str(), nullptr, true);
      std::this_thread::sleep_for(std::chrono::milliseconds(300));
      std::cout << "{\"posted\":true}" << std::endl;
      continue;
    }
    if (request.get<std::string>("action", "") == "paste") {
      const auto mimeType = request.get<std::string>("mimeType");
      const auto data = request.get<std::string>("data");
      const bool ok = doc->pClass->paste(doc, mimeType.c_str(), data.data(), data.size());
      std::cout << "{\"pasted\":" << (ok ? "true" : "false") << "}" << std::endl;
      continue;
    }
    if (request.get<std::string>("action", "") == "paint") {
      const int width = request.get<int>("width"), height = request.get<int>("height");
      std::vector<unsigned char> buffer(static_cast<std::size_t>(width) * height * 4);
      doc->pClass->paintTile(doc, buffer.data(), width, height, request.get<int>("x"),
                             request.get<int>("y"), request.get<int>("tileWidth"),
                             request.get<int>("tileHeight"));
      std::ofstream(request.get<std::string>("file"), std::ios::binary)
          .write(reinterpret_cast<const char *>(buffer.data()), static_cast<std::streamsize>(buffer.size()));
      std::cout << "{\"painted\":true,\"bytes\":" << buffer.size() << "}" << std::endl;
      continue;
    }
    if (request.get<std::string>("action", "") == "save") {
      const bool ok = doc->pClass->saveAs(doc, request.get<std::string>("url").c_str(), "ods", nullptr);
      std::cout << "{\"saved\":" << (ok ? "true" : "false") << "}" << std::endl;
      continue;
    }
    if (request.get<std::string>("action", "") == "lok-select") {
      doc->pClass->setPart(doc, request.get<int>("part", 0));
      const auto address = request.get<std::string>("address");
      const std::string args = "{\"ToPoint\":{\"type\":\"string\",\"value\":\"" + address + "\"}}";
      doc->pClass->postUnoCommand(doc, ".uno:GoToCell", args.c_str(), false);
      std::this_thread::sleep_for(std::chrono::milliseconds(150));
      char *cursor = doc->pClass->getCommandValues(doc, ".uno:CellCursor");
      std::cout << "{\"cursor\":" << (cursor ? cursor : "null") << "}" << std::endl;
      std::free(cursor);
      continue;
    }
    const int part = request.get<int>("part", 0);
    const std::string text = request.get<std::string>("text", "");
    char *raw = oxsdk_calc_cell_model(doc, part,
        request.get<int>("column", 0), request.get<int>("row", 0),
        request.get<int>("operation", 0), text.data(), text.size(), request.get<int>("enabled", 0));
    std::cout << (raw ? raw : "{\"ok\":false,\"code\":\"ALLOCATION_FAILED\"}") << std::endl;
    std::free(raw);
  }
  doc->pClass->destroy(doc);
  kit->pClass->destroy(kit);
}
