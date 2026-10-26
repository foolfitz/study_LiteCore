#ifndef V23_NATIVE_S5_SEQUENCE_HPP
#define V23_NATIVE_S5_SEQUENCE_HPP
#include <array>
#include <stdexcept>
#include <string>
#include <vector>
namespace v23s5 {
struct Post { int character; int key; std::string operation; };
inline const std::array<const char*,7> families = {{"backspace", "delete", "type", "backspace-twice", "delete-twice", "backspace-before-and-after", "delete-before-and-after"}};
inline std::vector<Post> sequence(const std::string& family, int shiftKey, const std::string& keyName) {
    const Post shift{0, shiftKey | 0x1000, "Shift+" + keyName};
    const Post back{0,1283,"Backspace"}, del{0,1286,"Delete"}, text{120,0,"text:x"};
    if (family=="backspace") return {shift,back};
    if (family=="delete") return {shift,del};
    if (family=="type") return {shift,text};
    if (family=="backspace-twice") return {shift,back,back};
    if (family=="delete-twice") return {shift,del,del};
    if (family=="backspace-before-and-after") return {back,shift,back};
    if (family=="delete-before-and-after") return {del,shift,del};
    throw std::invalid_argument("unknown S5 family");
}
// Only two FIFO key calls per original member; no read, paste, wait or save seam.
template<typename Send> void dispatch(const std::vector<Post>& posts, Send send) {
    for (const auto& post : posts) {
        send(0,post.character,post.key); // LOK_KEYEVENT_KEYINPUT
        send(1,post.character,post.key); // LOK_KEYEVENT_KEYUP
    }
}
}
#endif
