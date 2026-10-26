// Native S5 type-family references, run 02 (fable ruling 3, 2026-10-27).
// run-01 posted Shift+key and x back to back and measured x-then-Shift in 56/56 type
// cells.  Here the Shift member settles (the existing 800 ms quiet / 8000 ms cap) and
// its selection is read before x is posted; the read is the per-cell order witness.
// Reuses the archived signature setup and the unchanged S5 sequence header; run-01's
// harness (v23_native_s5.cpp) is not modified, so run-01 stays re-readable.
#define main v23_retained_signature_main
#include "link_native_extend_signatures.cpp"
#undef main
#include "v23_native_s5_sequence.hpp"
#include <filesystem>

static_assert(LOK_KEYEVENT_KEYINPUT==0 && LOK_KEYEVENT_KEYUP==1, "S5 recording protocol follows actual LOK event enums");

namespace {
const char* const kFamily="type";
std::string sequenceJson(const std::vector<v23s5::Post>& seq) {
    std::string out="[";
    for (std::size_t i=0;i<seq.size();++i) out+=(i?",":"")+q(seq[i].operation);
    return out+"]";
}
std::string cellId(const KeyDef& k,const std::string& shape) {
    return "shift-"+std::string(k.name)+"@"+shape+"/"+kFamily;
}
bool nativeKey(const KeyDef& k) {
    return std::string(k.name)=="Left" || std::string(k.name)=="Right" ||
           std::string(k.name)=="Home" || std::string(k.name)=="End";
}
void inventory() {
    for (const auto& shape:kShapes) for (const auto& k:kKeys) if (nativeKey(k))
        std::cout<<"{\"id\":"<<q(cellId(k,shape))<<",\"sequence\":"
                 <<sequenceJson(v23s5::sequence(kFamily,k.code,k.name))<<"}\n";
}
bool measured(LibreOfficeKit* kit,const std::string& url,const std::filesystem::path& out,
              const std::string& shape,const KeyDef& k) {
    const auto id=cellId(k,shape);
    std::string stem=id;std::replace(stem.begin(),stem.end(),'/','_');
    const auto beforeFile=out/(stem+"-before.odt"),afterFile=out/(stem+"-after.odt");
    if (std::filesystem::exists(beforeFile)||std::filesystem::exists(afterFile)) return false;
    const auto seq=v23s5::sequence(kFamily,k.code,k.name);
    if (seq.size()!=2) return false;
    Doc s=openDoc(kit,url);
    if (!s.d) {std::cout<<"{\"id\":"<<q(id)<<",\"fatal\":\"documentLoad\"}\n";return false;}
    const auto opened=settle(s,800,8000);
    const auto made=makeShape(s,shape,800);
    const auto before=snap(s);
    const auto saveBefore=s.d->pClass->saveAs(s.d,("file://"+beforeFile.string()).c_str(),"odt",nullptr)!=0;
    const auto beforePost=snap(s);
    const int beforeType=s.d->pClass->getSelectionType(s.d);
    const auto start=nowMs();
    struct Sent {int type,character,key;double at,returned;};
    std::vector<Sent> sent;sent.reserve(seq.size()*2);
    const auto post=[&](const v23s5::Post& member) {
        v23s5::dispatch({member},[&](int type,int character,int code) {
            const auto at=nowMs();
            s.d->pClass->postKeyEvent(s.d,type,character,code);
            sent.push_back({type,character,code,at-start,nowMs()-start});
        });
    };
    post(seq[0]);
    // The ruling's reference-side settle; x is posted even after a cap so the record is
    // complete, and the reader reads such a cell NE.
    const auto shiftSettled=settle(s,800,8000);
    const auto readStart=nowMs()-start;
    const auto between=snap(s);
    const int betweenType=s.d->pClass->getSelectionType(s.d);
    const auto readEnd=nowMs()-start;
    // 'x' is queued KEYINPUT(character=120,key=0), never synchronous paste.
    post(seq[1]);
    const auto settled=settle(s,800,8000);
    const auto after=snap(s);
    const int afterType=s.d->pClass->getSelectionType(s.d);
    const auto saveAfter=s.d->pClass->saveAs(s.d,("file://"+afterFile.string()).c_str(),"odt",nullptr)!=0;
    std::cout<<"{\"id\":"<<q(id)<<",\"shape\":"<<q(shape)<<",\"key\":"<<q(k.name)
             <<",\"family\":"<<q(kFamily)<<",\"sequence\":"<<sequenceJson(seq)
             <<",\"mode\":\"default-native-queued\",\"interMemberSettle\":{\"after\":"<<q(seq[0].operation)
             <<",\"quietMs\":800,\"capMs\":8000},\"openedSettleMs\":"<<opened
             <<",\"setupSettleMs\":"<<made.settleMs<<",\"shiftSettleMs\":"<<shiftSettled
             <<",\"finalSettleMs\":"<<settled
             <<",\"expectedSelection\":"<<q(made.expectedSelection)
             <<",\"expectedCursorPoint\":"<<q(made.expectedCursorPoint)
             <<",\"expectedCursorRect\":"<<q(made.expectedCursorPoint.empty()?"":pt(made.expectedCursorPoint).rect)
             <<",\"beforeSelectionType\":"<<beforeType<<",\"betweenSelectionType\":"<<betweenType
             <<",\"afterSelectionType\":"<<afterType
             <<",\"before\":"<<snapJson(before)<<",\"beforePost\":"<<snapJson(beforePost)
             <<",\"between\":"<<snapJson(between)<<",\"betweenReadStartMs\":"<<readStart
             <<",\"betweenReadEndMs\":"<<readEnd
             <<",\"after\":"<<snapJson(after)<<",\"savedBefore\":"<<(saveBefore?"true":"false")
             <<",\"savedAfter\":"<<(saveAfter?"true":"false")
             <<",\"beforeFile\":"<<q(beforeFile.filename().string())
             <<",\"afterFile\":"<<q(afterFile.filename().string())<<",\"posts\":[";
    for (std::size_t i=0;i<sent.size();++i) {
        const auto& p=sent[i];
        std::cout<<(i?",":"")<<"{\"type\":"<<p.type<<",\"character\":"<<p.character
                 <<",\"key\":"<<p.key<<",\"atMs\":"<<p.at<<",\"returnMs\":"<<p.returned<<"}";
    }
    std::cout<<"],\"callbacks\":"<<callbacksJson(s,start,-500)<<"}"<<std::endl;
    closeDoc(s);
    // A Shift-settle cap is that cell's missing witness (fallback A), not a run failure.
    return saveBefore&&saveAfter&&opened>=0&&made.settleMs>=0&&settled>=0;
}
}
int main(int argc,char** argv) {
    if(argc==2&&std::string(argv[1])=="--inventory") {inventory();return 0;}
    if(argc==2&&std::string(argv[1])=="--paragraphs") return v23_retained_signature_main(argc,argv);
    if(argc!=5) {std::cerr<<"usage: v23-native-s5-type INSTALL PROFILE_URL FIXTURE_URL FRESH_SAVE_DIRECTORY\n";return 2;}
    const std::filesystem::path out=std::filesystem::absolute(argv[4]);
    if(!std::filesystem::is_directory(out)||!std::filesystem::is_empty(out)) return 2;
    // run-02 printed the default six significant digits: past 1000 ms the between-read end
    // and the x post rounded to the same 0.01 ms in 46 cells, so the order was unwitnessable.
    std::cout.precision(15);
    LibreOfficeKit* kit=lok_init_2(argv[1],argv[2]);if(!kit)return 3;
    if(!discoverAll(kit,argv[3],1,800))return 4;
    bool ok=true;
    for(const auto& shape:kShapes)for(const auto& k:kKeys)if(nativeKey(k))
        if(!measured(kit,argv[3],out,shape,k))ok=false;
    return ok?0:5;
}
