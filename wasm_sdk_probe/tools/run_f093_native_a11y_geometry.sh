#!/usr/bin/env bash
# Finding 093, option B, step 1 -- native calibration of the coordinate space.
#
# The runbook's section 2 is read from source, not measured.  This run measures
# it on `build-native-26-8`, which is rebuildable, mints no wasm identity and
# voids no evidence.  The wasm relink is the one-way door; this is the look
# behind it.
#
# The criteria were registered BEFORE either half of the probe was written:
# findings/evidence/093/step1-native-geometry/ACCEPTANCE.md, commit bcb7caf4.
# Judging is offline (tools/analyze_f093_native_geometry.py) so the run and the
# criteria stay separable and either can be re-run against the other's output.
#
# The probe compiles into its own output directory.  It never touches a
# profile's build directory, and it never touches dist/.
#
# Usage: tools/run_f093_native_a11y_geometry.sh [OUTPUT_DIR]

set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$(cd "$here/../libreoffice-26-8" && pwd)"
build="$(cd "$here/../build-native-26-8" && pwd)"
out="${1:-$here/../findings/evidence/093/step1-native-geometry/run}"
# LO builds its user-installation URL as `file://$profile_dir`, so a relative
# OUTPUT_DIR produces `file://../...` and the kit dies in userinstall before a
# single measurement is taken.
mkdir -p "$out"
out="$(cd "$out" && pwd)"

install_dir="$build/instdir/program"
[ -d "$install_dir" ] || { echo "native build not found at $install_dir" >&2; exit 1; }

# One round is one record.
if [ -f "$out/captures.jsonl" ]; then
  echo "refusing to overwrite an existing round: $out/captures.jsonl" >&2
  echo "pass a different OUTPUT_DIR" >&2
  exit 2
fi

profile_dir="$out/user-profile"
rm -rf "$profile_dir"; mkdir -p "$profile_dir"

bridge_o="$out/f093_bridge.o"
probe="$out/f093-native-a11y-geometry"

echo "== compiling the core-internal half =="
# `-std=c++20 -DLIBO_INTERNAL_ONLY` is how core compiles itself.  Exactly one
# translation unit gets it; the LOK client half must not, because the define
# changes what the public headers present.
g++ -std=c++20 -O2 -fPIC \
  -DLIBO_INTERNAL_ONLY -DCPPU_ENV=gcc3 -DUNX -DLINUX -DX86_64 \
  -I"$src/include" \
  -I"$build/config_host" \
  -I"$build/workdir/UnoApiHeadersTarget/udkapi/comprehensive" \
  -I"$build/workdir/UnoApiHeadersTarget/offapi/comprehensive" \
  -I"$build/workdir/UnpackedTarball/boost" \
  -c "$here/tools/f093_native_a11y_geometry_bridge.cpp" -o "$bridge_o"

echo "== compiling and linking the LOK client half =="
g++ -std=c++17 -O2 -I"$src/include" \
  "$here/tools/f093_native_a11y_geometry.cpp" "$bridge_o" \
  -L"$install_dir" -lsfxlo -lvcllo -lcomphelper -ltllo \
  "$install_dir/libuno_sal.so.3" \
  "$install_dir/libuno_cppu.so.3" \
  "$install_dir/libuno_cppuhelpergcc3.so.3" \
  -Wl,-rpath,"$install_dir" -ldl -o "$probe"

# The fixture is generated into the run rather than taken from dist/: the
# question needs a document taller than the output window, with a unique marker
# at the head of every paragraph, and dist/ is identity-bound territory this
# task must not write to.
#
# Six A4 pages at 18 paragraphs a page.  Six pages is ~100,000 twips of
# document, which is what makes O-2 ("the last probed paragraph's y exceeds the
# window height") a real test rather than an unreached branch.
fixture="$out/f093-geometry.odt"
python3 "$here/tools/create_long_document.py" --pages 6 --out "$fixture" >/dev/null
fixture_sha="$(sha256sum "$fixture" | cut -d' ' -f1)"

core_commit="$(git -C "$src" rev-parse HEAD)"
tree_commit="$(git -C "$here/.." rev-parse HEAD)"

# The targets, in document order, spread over all six pages.  TWENTY of them,
# and the count is not decorative: the acceptance's R-1 pairs row i with the
# caret of row i+10, so there have to be twenty rows for "at least ten probed
# positions away" to be satisfiable at all.  Ten positions here is at least
# fifty paragraphs of separation -- two orders of magnitude past the two-line
# tolerance C2 allows, which is what makes a red case that stays red.
markers=(
  LD-P01-L02 LD-P01-L07 LD-P01-L12 LD-P01-L17
  LD-P02-L04 LD-P02-L10 LD-P02-L16
  LD-P03-L03 LD-P03-L09 LD-P03-L15
  LD-P04-L02 LD-P04-L08 LD-P04-L14
  LD-P05-L03 LD-P05-L09 LD-P05-L15
  LD-P06-L02 LD-P06-L08 LD-P06-L14 LD-P06-L17
)

python3 - "$out/context.json" "$core_commit" "$tree_commit" "$fixture" \
    "$fixture_sha" "${markers[@]}" <<'PY'
import json, sys
out, core, tree, fixture, sha = sys.argv[1:6]
json.dump({"schemaVersion": 1,
           "finding": "093",
           "step": "option-B-step-1-native-calibration",
           "acceptance": "findings/evidence/093/step1-native-geometry/"
                         "ACCEPTANCE.md (commit bcb7caf4)",
           "arm": "native",
           "coreBuild": "build-native-26-8",
           "coreCommit": core,
           "treeCommit": tree,
           "fixture": fixture,
           "fixtureSha256": sha,
           "markers": sys.argv[6:]},
          open(out, "w"), indent=2)
PY

echo "== running probe =="
set +e
SAL_USE_VCLPLUGIN=svp "$probe" "$install_dir" "file://$profile_dir" \
  "file://$fixture" "${markers[@]}" >"$out/captures.jsonl" 2>"$out/sal.log"
status=$?
set -e
echo "== probe exit: $status =="
echo
echo "Judge with:"
echo "  python3 tools/analyze_f093_native_geometry.py $out"
