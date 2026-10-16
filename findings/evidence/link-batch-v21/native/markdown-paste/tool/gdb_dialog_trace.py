# gdb -batch -x gdb_dialog_trace.py --args md-paste-probe ...
#
# Diagnostic for the empty-input arm (M13): does the paste reach the reader,
# does the reader fail, is the error MessageDialog created, and what does
# Dialog::ImplStartExecute return (false = cancelled before any modal loop,
# vcl/source/window/dialog.cxx:900-921 in LOK when the dialog has no notifier)?
# Prints one "TRACE ..." line per event; never stops the process.
import gdb

gdb.execute("set pagination off")
gdb.execute("set breakpoint pending on")
gdb.execute("set print thread-events off")
gdb.execute("handle SIGPIPE nostop noprint pass")


class Finish(gdb.FinishBreakpoint):
    def __init__(self, frame, label):
        super().__init__(frame, internal=True)
        self.label = label

    def stop(self):
        # Release build without debug info: return_value is None, so read the
        # x86-64 return register (bool -> low byte of rax, short -> low 16 bits).
        rax = int(gdb.parse_and_eval("$rax")) & 0xffffffffffffffff
        print("TRACE return %s = %s (rax low byte %d, low 16 bits %d)" % (
            self.label, self.return_value, rax & 0xff, rax & 0xffff))
        return False

    def out_of_scope(self):
        print("TRACE return %s = (out of scope)" % self.label)


class Trace(gdb.Breakpoint):
    def __init__(self, spec, label, want_return=False):
        super().__init__(spec, internal=False)
        self.label = label
        self.want_return = want_return

    def stop(self):
        print("TRACE enter %s" % self.label)
        if self.want_return:
            try:
                Finish(gdb.newest_frame(), self.label)
            except Exception as error:  # noqa: BLE001
                print("TRACE finish-breakpoint failed for %s: %s" % (self.label, error))
        return False


Trace("SwTransferable::PasteFileContent", "SwTransferable::PasteFileContent", True)
Trace("SwReader::Read", "SwReader::Read", False)
Trace("SwMarkdownParser::CallParser", "SwMarkdownParser::CallParser", False)
Trace("MessageDialog::MessageDialog(vcl::Window*, rtl::OUString, VclMessageType, VclButtonsType)",
      "MessageDialog ctor", False)
Trace("SalInstanceDialog::run", "SalInstanceDialog::run", True)
Trace("Dialog::Execute", "Dialog::Execute", True)
Trace("Dialog::ImplStartExecute", "Dialog::ImplStartExecute", True)

gdb.execute("run")
