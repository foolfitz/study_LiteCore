// Native driver for SPEC-M4-cell-editing-v1. It emits observations, not verdicts.
#define LOK_USE_UNSTABLE_API
#include <LibreOfficeKit/LibreOfficeKit.h>
#include <LibreOfficeKit/LibreOfficeKitEnums.h>
#include <LibreOfficeKit/LibreOfficeKitInit.h>
#include "../src/calc_cell_bridge.h"
#include <boost/property_tree/json_parser.hpp>
#include <boost/property_tree/ptree.hpp>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <thread>
#include <chrono>

int main(int argc, char **argv) {
  if (argc != 4) return 2;
  auto *kit = lok_init_2(argv[1], argv[2]);
  if (!kit) return 3;
  auto *doc = kit->pClass->documentLoad(kit, argv[3]);
  if (!doc) return 4;
  doc->pClass->initializeForRendering(doc, nullptr);
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
    if (request.get<std::string>("action", "") == "uno") {
      doc->pClass->postUnoCommand(doc, request.get<std::string>("command").c_str(), nullptr, true);
      std::this_thread::sleep_for(std::chrono::milliseconds(300));
      std::cout << "{\"posted\":true}" << std::endl;
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
