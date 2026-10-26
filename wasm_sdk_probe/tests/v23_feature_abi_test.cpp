#include "editor_api.h"
#include "probe_engine.hpp"
#include <cstdint>
#include <stdexcept>
static unsigned calls=0, mapped=0, maskAction=0, mask=0;
static bool throws=false, forwardedExtend=false, forwardedEnabled=false;
namespace probe {
SubmitStatus editorAction(std::uint32_t r,std::uint32_t d,std::uint32_t rev,std::uint32_t action,bool extend,bool enabled) {
  if (throws) throw std::runtime_error("test");
  if (!r || !d || rev!=0xffffffffu) return SubmitStatus::InternalError;
  ++calls; mapped=action; forwardedExtend=extend; forwardedEnabled=enabled; return SubmitStatus::Ok;
}
void editorSetActionGestures(std::uint32_t a,std::uint32_t m) {maskAction=a;mask=m;}
SubmitStatus editorGetState(std::uint32_t,std::uint32_t){return SubmitStatus::Ok;}
SubmitStatus editorPlaceCaret(std::uint32_t,std::uint32_t,std::int32_t,std::int32_t){return SubmitStatus::Ok;}
SubmitStatus editorSelect(std::uint32_t,std::uint32_t,std::uint32_t,int,int,int,int,bool){return SubmitStatus::Ok;}
}
int main() {
  if (oxsdk_editor_abi_version()!=EXPECTED_ABI) return 1;
  const unsigned maps[]={0,1,2,7,8,9,10,13,14,20,21,17,18,19,16,15,3,4,5,6,22,23,24,25};
  const unsigned bound=EXPECTED_ABI==4?21:23;
  for(unsigned action=0;action<=24;++action) {
    for(unsigned extend=0;extend<=2;++extend) for(unsigned enabled=0;enabled<=2;++enabled) {
      const bool move=action==1||action==2||(EXPECTED_ABI==6&&action>=16&&action<=19);
      const bool format=action>=7&&action<=10;
      const bool allowed=action>=1&&action<=bound&&extend<=1&&enabled<=1&&(!extend||move)&&(!enabled||format);
      const auto before=calls;
      auto status=oxsdk_editor_action(0xffffffffu,1,0xffffffffu,action,extend,enabled);
      if ((status==OXSDK_STATUS_OK)!=allowed || calls!=before+(allowed?1:0)) return 2;
      if (allowed&&(mapped!=maps[action]||forwardedExtend!=(extend!=0)||forwardedEnabled!=(enabled!=0))) return 3;
    }
    if ((oxsdk_editor_set_action_gestures(action,7)==OXSDK_STATUS_OK)!=(action>=1&&action<=bound)) return 4;
    if (action>=1&&action<=bound&&(maskAction!=maps[action]||mask!=7)) return 5;
  }
  if (oxsdk_editor_set_action_gestures(21,0)!=0||maskAction!=23||mask!=0) return 6;
  if (oxsdk_editor_set_action_gestures(1,8)!=OXSDK_STATUS_INVALID_ARGUMENT) return 7;
  if (oxsdk_editor_action(0,1,0xffffffffu,1,0,0)!=OXSDK_STATUS_INVALID_ARGUMENT) return 8;
  if (oxsdk_editor_action(1,0,0xffffffffu,1,0,0)!=OXSDK_STATUS_INVALID_ARGUMENT) return 9;
  throws=true;
  if (oxsdk_editor_action(1,1,0xffffffffu,1,0,0)!=OXSDK_STATUS_INTERNAL_ERROR) return 10;
  return 0;
}
