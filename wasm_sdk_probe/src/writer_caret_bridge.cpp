// SPEC-P-demo-batch-4 (finding 180): paragraph state read from the document.  Every
// earlier read had to select something, and a selection has to be undone: by
// coordinates (finding 180: the text moved) or by stepping one character (a
// one-character selection does not serialise the list, N3).  The HTML read of a
// range has its own blind spot: a range that starts inside a paragraph loses that
// paragraph's style (N3).  This read selects nothing and sees whole paragraphs.
// Only this TU uses internal headers.
#include "writer_caret_bridge.h"
#ifndef LOK_USE_UNSTABLE_API
#define LOK_USE_UNSTABLE_API
#endif
#include <LibreOfficeKit/LibreOfficeKit.h>

#include <sfx2/lokhelper.hxx>
#include <sfx2/viewsh.hxx>
#include <vcl/svapp.hxx>
#include <com/sun/star/beans/PropertyValue.hpp>
#include <com/sun/star/beans/XPropertySet.hpp>
#include <com/sun/star/container/XEnumeration.hpp>
#include <com/sun/star/container/XEnumerationAccess.hpp>
#include <com/sun/star/container/XIndexAccess.hpp>
#include <com/sun/star/container/XIndexReplace.hpp>
#include <com/sun/star/frame/XModel.hpp>
#include <com/sun/star/lang/XServiceInfo.hpp>
#include <com/sun/star/style/NumberingType.hpp>
#include <com/sun/star/style/ParagraphAdjust.hpp>
#include <com/sun/star/text/XTextRange.hpp>
#include <rtl/ustring.hxx>

#include <exception>
#include <map>

namespace {
using namespace com::sun::star;
using uno::Reference;
using probe::WriterParagraphRead;

// Named list styles repeat across a long selection, and building the rules object
// is the expensive part of this read.
using ListKinds = std::map<OUString, std::string>;

std::string listTagOf(const Reference<beans::XPropertySet> &paragraph, ListKinds &kinds) {
  OUString name;
  paragraph->getPropertyValue(u"NumberingStyleName"_ustr) >>= name;
  // The outline rule on a heading is not a list (cache-freshness/run-01: core's
  // SelectionHasNumber counts it, listNumber read true on every heading).
  if (name.isEmpty() || name == "Outline")
    return std::string();
  sal_Int16 level = 0;
  paragraph->getPropertyValue(u"NumberingLevel"_ustr) >>= level;
  const OUString key = name + "/" + OUString::number(level);
  const auto known = kinds.find(key);
  if (known != kinds.end())
    return known->second;
  Reference<container::XIndexReplace> rules;
  paragraph->getPropertyValue(u"NumberingRules"_ustr) >>= rules;
  std::string kind;
  if (rules.is() && level >= 0 && level < rules->getCount()) {
    uno::Sequence<beans::PropertyValue> format;
    rules->getByIndex(level) >>= format;
    sal_Int16 type = style::NumberingType::NUMBER_NONE;
    for (const beans::PropertyValue &property : format)
      if (property.Name == "NumberingType")
        property.Value >>= type;
    if (type != style::NumberingType::NUMBER_NONE)
      kind = type == style::NumberingType::CHAR_SPECIAL
                     || type == style::NumberingType::BITMAP ? "ul" : "ol";
  }
  kinds.emplace(key, kind);
  return kind;
}

std::string blockTagOf(const OUString &style) {
  if (style.getLength() == 9 && style.startsWith("Heading ") && style[8] >= '1' && style[8] <= '9')
    return std::string("h") + static_cast<char>(style[8]);
  return "p";
}

std::string alignOf(const Reference<beans::XPropertySet> &paragraph) {
  const uno::Any value = paragraph->getPropertyValue(u"ParaAdjust"_ustr);
  sal_Int32 adjust = -1;
  if (!(value >>= adjust))
    return std::string();
  switch (static_cast<style::ParagraphAdjust>(adjust)) {
  case style::ParagraphAdjust_LEFT: return "left";
  case style::ParagraphAdjust_RIGHT: return "right";
  case style::ParagraphAdjust_CENTER: return "center";
  case style::ParagraphAdjust_BLOCK: return "justify";
  default: return std::string();
  }
}

bool readRange(const Reference<text::XTextRange> &range, std::vector<WriterParagraphRead> &out,
               std::string &reason, ListKinds &kinds) {
  Reference<container::XEnumerationAccess> access(range, uno::UNO_QUERY);
  if (!access.is()) {
    reason = "the range has no paragraphs to walk";
    return false;
  }
  const Reference<container::XEnumeration> paragraphs = access->createEnumeration();
  while (paragraphs->hasMoreElements()) {
    Reference<lang::XServiceInfo> info(paragraphs->nextElement(), uno::UNO_QUERY);
    if (!info.is() || !info->supportsService(u"com.sun.star.text.Paragraph"_ustr)) {
      reason = "the selection holds a table";
      return false;
    }
    Reference<beans::XPropertySet> paragraph(info, uno::UNO_QUERY_THROW);
    Reference<text::XTextRange> text(info, uno::UNO_QUERY_THROW);
    OUString style;
    paragraph->getPropertyValue(u"ParaStyleName"_ustr) >>= style;
    WriterParagraphRead read;
    read.style = style.toUtf8().getStr();
    read.block = blockTagOf(style);
    read.list = listTagOf(paragraph, kinds);
    read.align = alignOf(paragraph);
    read.text = text->getString().toUtf8().getStr();
    out.push_back(std::move(read));
  }
  return true;
}
} // namespace

namespace probe {

bool writerSelectionParagraphs(void *lokDocument, std::vector<WriterParagraphRead> &out,
                               std::string &reason) {
  out.clear();
  reason.clear();
  try {
    SolarMutexGuard guard;
    auto *document = static_cast<LibreOfficeKitDocument *>(lokDocument);
    auto *shell = SfxLokHelper::getViewOfId(document->pClass->getView(document));
    if (!shell) {
      reason = "no view shell";
      return false;
    }
    const Reference<frame::XModel> model = shell->GetCurrentDocument();
    // Text: a collection of ranges, one for a caret too.  A frame or cells: not this.
    Reference<container::XIndexAccess> ranges(model->getCurrentSelection(), uno::UNO_QUERY);
    if (!ranges.is()) {
      reason = "the selection is not text";
      return false;
    }
    ListKinds kinds;
    for (sal_Int32 index = 0, count = ranges->getCount(); index < count; ++index) {
      Reference<text::XTextRange> range(ranges->getByIndex(index), uno::UNO_QUERY);
      if (!range.is()) {
        reason = "the selection is not text";
        return false;
      }
      if (!readRange(range, out, reason, kinds))
        return false;
    }
    if (out.empty()) {
      reason = "the selection covers no paragraph";
      return false;
    }
    return true;
  } catch (const uno::Exception &error) {
    reason = error.Message.toUtf8().getStr();
  } catch (const std::exception &error) {
    reason = error.what();
  }
  return false;
}

} // namespace probe
