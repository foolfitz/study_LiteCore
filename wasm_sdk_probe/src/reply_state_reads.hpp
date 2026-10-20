#ifndef OXOFFICE_REPLY_STATE_READS_HPP
#define OXOFFICE_REPLY_STATE_READS_HPP

// SPEC-M3-ordered-commands 15.2 (fable ruling 2 2.2): the STATE_CHANGED items a
// reply may read, by the command it answers.
//
// "STATE_CHANGED is timer class" was withdrawn: N1 measured the split per
// item, not per type -- `.uno:Bold` arrives in the command's own flush, the
// table and clipboard states do not.  A reply may decide on an item only if
// (command, item) is on the on-time list that read_n1.py --on-time-list
// generates from the native records (form 2), and
// tests/test_reply_state_reads.py holds this table against that list: an
// entry here that the list does not carry as on time in every round is red.
//
// Today the only readers are 059's check on the four inline formats
// (inlineFormatArgumentResolved): Writer answers them at a collapsed caret
// with `success:false` while applying them, so the state item is the witness.
// The `state` object every reply serialises is a report, not a decision, and
// is not listed.

namespace probe {
namespace replystate {

struct Read {
  const char *unoCommand;
  const char *stateKey;
};

inline constexpr Read kReads[] = {
    {".uno:Bold", ".uno:Bold"},
    {".uno:Italic", ".uno:Italic"},
    {".uno:Underline", ".uno:Underline"},
    {".uno:Strikeout", ".uno:Strikeout"},
};

} // namespace replystate
} // namespace probe

#endif
