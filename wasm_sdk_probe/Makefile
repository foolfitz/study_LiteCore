LOSRC ?= ../libreoffice-26-8
LOBUILD ?= ../wasm-lite/build-headless-probe

EMSDK_ROOT ?= ../wasm-lite/tools/emsdk
CXX := $(EMSDK_ROOT)/upstream/emscripten/em++
HOST_CXX ?= g++
CPPFLAGS := -DLOK_USE_UNSTABLE_API -I$(LOSRC)/include \
	-I$(LOBUILD)/config_host \
	-I$(LOBUILD)/workdir/UnoApiHeadersTarget/udkapi/comprehensive
E1_CPPFLAGS := $(CPPFLAGS) \
	-I$(LOBUILD)/workdir/UnoApiHeadersTarget/offapi/comprehensive \
	-I$(LOBUILD)/workdir/UnpackedTarball/boost
CXXFLAGS := -O1 -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm
R5_CXXFLAGS := -Oz -pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm

SOURCES := src/probe_api.cpp src/sdk_api.cpp src/probe_engine.cpp src/unoembind_stub.cpp
OBJECTS := $(SOURCES:.cpp=.o)
HEADERS := src/probe_api.h src/sdk_api.h src/probe_engine.hpp
CORE_EXPORTS := $(LOBUILD)/workdir/CustomTarget/desktop/soffice_bin-emscripten-exports/exports
LINKDEPS := $(LOBUILD)/instdir/program/soffice.js.linkdeps
FS_PRE_JS := $(LOBUILD)/workdir/CustomTarget/static/emscripten_fs_image/soffice.data.js.link
CORE_DATA := $(LOBUILD)/instdir/program/soffice.data
CORE_METADATA := $(LOBUILD)/instdir/program/soffice.data.js.metadata
CORE_COMMIT := $(shell git -C $(LOSRC) rev-parse HEAD)
R5_BUILD := build/r5
R5_SOURCES := src/sdk_api.cpp src/probe_engine.cpp src/unoembind_stub.cpp
R5_REVIEW_OBJECTS := $(patsubst src/%.cpp,$(R5_BUILD)/writer-review/%.o,$(R5_SOURCES))
R5_READER_OBJECTS := $(patsubst src/%.cpp,$(R5_BUILD)/writer-reader/%.o,$(R5_SOURCES))
R7_COMPAT_FILES := $(notdir $(wildcard test-docs/r7-compat/*))
FINDING_012_FILES := $(notdir $(wildcard test-docs/r7-finding-012/*))
FINDING_012_BUILD := build/finding-012
FINDING_012_DIAGNOSTIC_BUILD := $(FINDING_012_BUILD)/diagnostic
FINDING_012_DIAGNOSTIC_OBJECTS := $(patsubst src/%.cpp,$(FINDING_012_DIAGNOSTIC_BUILD)/%.o,$(R5_SOURCES))
FINDING_012_DIAGNOSTIC_DIST := dist/profiles/finding-012-diagnostic
E1_BUILD := build/e1/editor-discovery
E1_DIST := dist/profiles/e1-editor-discovery
E1_SOURCES := src/sdk_api.cpp src/probe_engine.cpp src/unoembind_stub.cpp \
	src/editor_discovery_api.cpp
E1_OBJECTS := $(patsubst src/%.cpp,$(E1_BUILD)/%.o,$(E1_SOURCES))
E1_FIXTURE_FILES := $(notdir $(wildcard test-docs/e1/*.odt))
E1_B_BUILD := build/e1/editor-v1
E1_B_DIST := dist/profiles/e1-editor-v1
E1_B_SOURCES := src/sdk_api.cpp src/probe_engine.cpp src/unoembind_stub.cpp \
	src/editor_api.cpp
E1_B_OBJECTS := $(patsubst src/%.cpp,$(E1_B_BUILD)/%.o,$(E1_B_SOURCES))

# SPEC E2-B 5.12: the product v2 build variant.
#
# It is NOT a relink of e1-editor-v1.  The product objects there are compiled
# without -DOXSDK_E2_FORMAT_BARRIER and route C sits entirely inside that
# ifdef, so the shipped product has never contained the paragraph-format path
# at all -- "re-run on the product build" was describing a build that did not
# exist.  Same sources, three flags instead of two, its own output tree.
E2_B_BUILD := build/e2/editor-v2
E2_B_DIST := dist/profiles/e2-editor-v2
E2_B_SOURCES := $(E1_B_SOURCES)
E2_B_OBJECTS := $(patsubst src/%.cpp,$(E2_B_BUILD)/%.o,$(E2_B_SOURCES))

# finding 022 verification build: same flags as e1-editor-v1, separate output.
# The frozen e1-editor-v1 must not be rebuilt (SPEC E2-A section 3), so the fix
# is verified on its own artifact and the frozen one keeps carrying the bug
# until re-validating it is an explicit decision.
E1_FIX_BUILD := build/e1/editor-v1-noopfix
E1_FIX_DIST := dist/profiles/e1-editor-v1-noopfix
E1_FIX_OBJECTS := $(patsubst src/%.cpp,$(E1_FIX_BUILD)/%.o,$(E1_B_SOURCES))
E2_BUILD := build/e2/format-discovery
E2_DIST := dist/profiles/e2-format-discovery
E2_OBJECTS := $(patsubst src/%.cpp,$(E2_BUILD)/%.o,$(E1_SOURCES))
# Finding 021 attribution: same as E2 plus the Finding 016 scheduler drain, so
# the run can ask whether the missing state is core not computing it or this
# build never pumping the scheduler that would.
# Finding 037 / task 032: same sources and defines as e2-format-discovery, but
# linked with emscripten's pthread tracing.  Its own artifact, so the shipped
# one is never rebuilt.
E2_WAIT_BUILD := build/e2/wait-diagnostic
E2_WAIT_DIST := dist/profiles/e2-wait-diagnostic
E2_WAIT_OBJECTS := $(patsubst src/%.cpp,$(E2_WAIT_BUILD)/%.o,$(E1_SOURCES))
# Finding 040 / task 042: the E2 discovery family with the finding 037 guard
# compiled OUT and --profiling-funcs on.  037's hang is only reachable without
# the guard, and naming its parked frames needs a name section -- no existing
# artifact has both.  This is the build that decides the prediction in finding
# 040 section 5.  Diagnostic only: never shipped, never bound to a verdict.
E2_PREGUARD_BUILD := build/e2/preguard-profiling
E2_PREGUARD_DIST := dist/profiles/e2-preguard-profiling
E2_PREGUARD_OBJECTS := $(patsubst src/%.cpp,$(E2_PREGUARD_BUILD)/%.o,$(E1_SOURCES))
# Task #47 / SPEC E2-A 10.14's E2-B entry condition, under the C-plus ruling.
# The combination E2-B would actually ship, and which exists on no artifact
# today: the PRODUCT select ABI (the one that arms the bounded readback,
# editor_api.cpp:123) together with the format barrier, while still exporting
# the discovery ABI so the A3/A4/A5 harness can drive it unchanged.
#
# Both symbol sets on ONE hash on purpose.  The entry condition has two clauses
# -- "039 fixed" and "A3/A4/A5 re-swept and passing" -- and satisfying them on
# two different artifacts would satisfy neither.  Both API translation units put
# their helpers in anonymous namespaces, so linking them together is clean.
#
# Measurement profile: never shipped, and it does NOT change the discovery
# profile, which keeps pure callback semantics and keeps finding 039 by design
# (probe_engine.hpp:69-72).
E2_COMBO_BUILD := build/e2/combination
E2_B_TEXT_TEST_BIN := build/e2/format-readback-text-test
E2_COMBO_DIST := dist/profiles/e2-combination
E2_COMBO_SOURCES := src/sdk_api.cpp src/probe_engine.cpp src/unoembind_stub.cpp \
	src/editor_api.cpp src/editor_discovery_api.cpp
E2_COMBO_OBJECTS := $(patsubst src/%.cpp,$(E2_COMBO_BUILD)/%.o,$(E2_COMBO_SOURCES))
E2_SCHED_BUILD := build/e2/scheduler-attribution
E2_SCHED_DIST := dist/profiles/e2-scheduler-attribution
E2_SCHED_OBJECTS := $(patsubst src/%.cpp,$(E2_SCHED_BUILD)/%.o,$(E1_SOURCES))
# Finding 021 candidate 1: same as E2 but the engine command loop is replaced
# by the upstream emscripten main loop entered through the public LOK runLoop
# API (unipoll).  No unit-test pump is linked; the question this profile
# answers is whether the production main loop alone keeps the format state
# fresh.
E2_MAINLOOP_BUILD := build/e2/mainloop-attribution
E2_MAINLOOP_DIST := dist/profiles/e2-mainloop-attribution
E2_MAINLOOP_OBJECTS := $(patsubst src/%.cpp,$(E2_MAINLOOP_BUILD)/%.o,$(E1_SOURCES))
# Finding 021 discriminating experiment 1: the main-loop engine PLUS the
# Finding 016 scheduler drain, so ProcessEventsToIdle can be measured under
# the live loop.  If PEI still releases watched payloads here, the
# PEI-vs-loop difference is in PEI's semantics; if it no longer does, the
# difference is in what the old non-unipoll init (full Desktop::Main) set up.
E2_MLPEI_BUILD := build/e2/mainloop-pei
E2_MLPEI_DIST := dist/profiles/e2-mainloop-pei-attribution
E2_MLPEI_OBJECTS := $(patsubst src/%.cpp,$(E2_MLPEI_BUILD)/%.o,$(E1_SOURCES))
# Finding 031 measurement: the scheduler-attribution profile with one thing
# changed -- it asks LOK for a zh-TW UI language at documentLoad.  The
# paragraph-style postcondition matches whole strings that come from core's
# UIName table, and that table is keyed by UI language, so this build is the
# other arm of a comparison whose first arm is every run so far.  The tag is
# compiled in rather than passed from JS: it is an experiment, not a surface.
E2_LOCALE_BUILD := build/e2/locale-attribution
E2_LOCALE_DIST := dist/profiles/e2-locale-attribution
E2_LOCALE_LANGUAGE := zh-TW
E2_LOCALE_OBJECTS := $(patsubst src/%.cpp,$(E2_LOCALE_BUILD)/%.o,$(E1_SOURCES))
FINDING_016_SCHEDULER_BUILD := build/finding-016/scheduler
FINDING_016_SCHEDULER_DIST := dist/profiles/finding-016-scheduler
FINDING_016_SCHEDULER_OBJECTS := $(patsubst src/%.cpp,$(FINDING_016_SCHEDULER_BUILD)/%.o,$(E1_SOURCES))
FINDING_016_SELECTION_BUILD := build/finding-016/selection-barrier
FINDING_016_SELECTION_DIST := dist/profiles/finding-016-selection-barrier
FINDING_016_SELECTION_OBJECTS := $(patsubst src/%.cpp,$(FINDING_016_SELECTION_BUILD)/%.o,$(E1_SOURCES))

.PHONY: all clean serve serve-r5 serve-demo r5 r5-profiles r6-discovery-assets \
	r6-reader-assets r6-contract-assets r6-reference-assets r6-assets \
	r7-discovery-assets \
	r7-reference-assets r7-compatibility-assets r7-longevity-assets r7-assets \
	r8-discovery-assets r8-delivery-assets r8-service-worker-assets \
	e1-discovery-profile e1-discovery-assets \
	e1-editor-profile e1-editor-assets e1-editor-validation-assets \
	demo-editor-assets f018-line-nav-assets e1-drag-select-gate-assets \
	f039-product-readback-assets \
	f039-composition-scan-assets \
	e2-combination-profile \
	e1-session-wedge-assets \
	e1-noopfix-profile e1-noopfix-assets \
	e2-format-discovery-profile e2-format-discovery-assets \
	e2-wait-diagnostic-profile e2-wait-diagnostic-assets \
	e2-scheduler-attribution-profile e2-scheduler-attribution-assets \
	e2-mainloop-attribution-profile e2-mainloop-attribution-assets \
	e2-mainloop-pei-attribution-profile e2-mainloop-pei-attribution-assets \
	e2-locale-attribution-profile e2-locale-attribution-assets \
	finding-016-scheduler-profile finding-016-scheduler-assets \
	finding-016-selection-barrier-profile finding-016-selection-barrier-assets \
	finding-012-assets finding-012-attribution-assets r7-remediation-assets \
	test-r2 test-r3 test-r4 test-r5 test-r6-a test-r6-b test-r6-c \
	test-r6-roundtrip test-r6-release test-r7-a-static test-r7-b-static \
	test-r7-c-static test-r7-d-static test-r8-a-static test-r8-b-static \
	test-r8-c-static test-r8-d-static \
	test-e1-a-static test-e1-b-static test-e1-c-static test-e2-a-static \
	test-e2-b-static \
	test-e1-c-frozen-guard test-e1-c-shell-bundle-tool \
	test-finding-016-scheduler-static \
	test-finding-016-selection-barrier-static \
	test-finding-012-static \
	test-finding-012-attribution test-finding-012-native-26-8 \
	test-finding-012-remediation

all: dist/probe.js dist/probe.wasm dist/soffice.data dist/soffice.data.js.metadata \
	 dist/index.html dist/app.js dist/r2.html dist/r2-app.js \
	 dist/r3.html dist/r3-app.js \
	 dist/r4.html dist/r4-app.js \
	 dist/document-sdk.js dist/document-sdk.d.ts dist/sdk-worker.js dist/sdk-manifest.json \
	 dist/provider-sdk/provider-sdk.js dist/provider-sdk/provider-sdk.d.ts \
	 dist/providers/text-translate-descriptor.js \
	 dist/providers/text-translate-provider.js dist/providers/text-translate-worker.js

r5: all r5-profiles dist/r5-reader.html dist/r5-reader-app.js

r6-discovery-assets: dist/r6-discovery.html dist/r6-discovery-app.js \
	dist/profiles/writer-review-r6/sdk-worker.js \
	dist/profiles/writer-review-r6/sdk-manifest.json \
	dist/r6-fixtures/t1-plain-zh.odt dist/r6-fixtures/t2-styled.odt \
	dist/r6-fixtures/t3-long.odt

r6-reader-assets: r6-discovery-assets dist/r6-reader.html dist/r6-reader-app.js \
	dist/r6.css dist/reader-shell/state-machine.js \
	dist/reader-shell/tile-scheduler.js dist/reader-shell/reader-session.js

r6-contract-assets: dist/collaboration/contract.js dist/collaboration/contract.d.ts \
	dist/collaboration/collaboration-client.js

r6-reference-assets: r6-reader-assets r6-contract-assets \
	dist/r6-reference.html dist/r6-reference-app.js \
	dist/provider-sdk/provider-sdk.js \
	dist/providers/text-translate-descriptor.js \
	dist/providers/text-translate-provider.js dist/providers/text-translate-worker.js

r6-assets: r6-reference-assets

r7-discovery-assets: r6-discovery-assets dist/r7-discovery.html \
	dist/r7-discovery-app.js dist/input/input-adapter.js \
	dist/r7-fixtures/manifest.json \
	dist/r7-fixtures/r7-plain.odt dist/r7-fixtures/r7-plain.docx \
	dist/r7-fixtures/r7-corrupt-truncated.odt \
	dist/r7-fixtures/r7-corrupt-truncated.docx \
	dist/r7-fixtures/r7-unknown.bin

r7-reference-assets: r7-discovery-assets dist/r7-reference.html \
	dist/r7-reference-app.js dist/r7.css dist/input/clipboard-adapter.js \
	dist/r7/page-navigation.js

r7-compatibility-assets: r7-reference-assets dist/r7-compatibility.html \
	dist/r7-compatibility-app.js dist/r7/document-preflight.js \
	$(addprefix dist/r7-compat-fixtures/,$(R7_COMPAT_FILES))

r7-longevity-assets: r7-compatibility-assets dist/r7-longevity.html \
	dist/r7-longevity-app.js

r7-assets: r7-longevity-assets

r8-discovery-assets: r7-assets dist/r8-discovery.html \
	dist/r8-discovery-app.js dist/r8-discovery-sw.js \
	dist/r8/release-schema-v1.json dist/r8/release-manifest.json

r8-delivery-assets: r8-discovery-assets dist/r8-delivery.html \
	dist/r8-delivery-app.js dist/delivery/verified-loader.js \
	dist/delivery/verified-loader.d.ts dist/releases/index.json

r8-service-worker-assets: r8-delivery-assets dist/r8-update.html \
	dist/r8-update-app.js dist/r8-service-worker.js \
	dist/delivery/release-state.js dist/delivery/release-state.d.ts \
	dist/r8c/release-set.json

e1-discovery-assets: e1-discovery-profile dist/e1-discovery.html \
	dist/e1-discovery-app.js dist/e1-manual-delete.html \
	dist/e1-manual-delete-app.js dist/e1/editor-discovery-client.js \
	dist/sdk/document-sdk.js dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-format-discovery-assets: e2-format-discovery-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/e2/discovery-matrix-v1.json \
	dist/sdk/document-sdk.js dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Task 036, route B.  Headings and lists shown on the artifact whose evidence
# describes them, because contract v2 is E2-B and E2-000 section 5 does not
# authorise E2-B before E2-A has a verdict.
#
# No `e2-format-discovery-profile` prerequisite, and that is the point: the
# demo is pinned to c89f069e and refuses to start against anything else, so a
# rule that could relink the profile out from under it would turn a deliberate
# expiry into a silent substitution.  Same reason as demo-editor-assets.
demo-structure-assets: dist/demo-structure.html dist/demo-structure-app.js \
	dist/e2/demo-structure-client.js dist/e2/format-discovery-client.js \
	dist/sdk/document-sdk.js dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Finding 039 reproduction.  Same rule as the demo: no profile prerequisite,
# because the behaviour is a property of the artifact already in dist and a
# relink would answer a different question.
f039-caret-reset-assets: dist/f039-caret-reset-repro.html \
	dist/f039-caret-reset-repro-app.js \
	dist/e2/format-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-scheduler-attribution-assets: e2-scheduler-attribution-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-locale-attribution-assets: e2-locale-attribution-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-mainloop-attribution-assets: e2-mainloop-attribution-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-mainloop-pei-attribution-assets: e2-mainloop-pei-attribution-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e1-editor-assets: e1-editor-profile dist/e1-editor.html \
	dist/e1-editor-app.js dist/sdk/document-sdk.js \
	dist/editor-shell/editor-client.js dist/editor-shell/editor-client.d.ts \
	dist/editor-shell/state-machine.js dist/editor-shell/editor-session.js \
	dist/input/input-adapter.js dist/input/clipboard-adapter.js \
	dist/reader-shell/tile-scheduler.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Finding 021 exposure check on the *already built* e1-editor-v1 profile.
# Deliberately does not depend on e1-editor-profile: rebuilding the frozen
# artifact is exactly what this check must not do.  It reads dist/profiles/
# e1-editor-v1 as shipped.
e1-noopfix-assets: e1-noopfix-profile e1-bold-noop-assets

e1-bold-noop-assets: dist/e1-bold-noop-check.html dist/e1-bold-noop-app.js \
	dist/sdk/document-sdk.js dist/editor-shell/editor-client.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Presentation shell over the *already built* e1-editor-v1 profile.  Like
# e1-bold-noop-assets it deliberately omits the e1-editor-profile prerequisite:
# the frozen artifact must not be rebuilt, because rebuilding it invalidates the
# manual Chewing evidence that E1-C's verdict depends on.
demo-editor-assets: dist/demo-editor.html dist/demo-editor-app.js \
	dist/sdk/document-sdk.js \
	dist/editor-shell/editor-client.js dist/editor-shell/state-machine.js \
	dist/editor-shell/editor-session.js dist/editor-shell/recovery-notice.js \
	dist/input/input-adapter.js dist/input/clipboard-adapter.js \
	dist/reader-shell/tile-scheduler.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Task 035: the finding 038 wedge driven through the product EditorSession
# rather than a bare NarrowEditorClient, to size option (d).  Same rule as
# demo-editor-assets -- no profile prerequisite, because the whole question is
# what today's frozen 835b453d does, and a rebuild would answer a different one.
e1-session-wedge-assets: dist/e1-session-wedge-recovery.html \
	dist/e1-session-wedge-recovery-app.js \
	dist/e1-post-wedge-liveness.html dist/e1-post-wedge-liveness-app.js \
	dist/e1-checkpoint-cost.html dist/e1-checkpoint-cost-app.js \
	dist/sdk/document-sdk.js \
	dist/editor-shell/editor-client.js dist/editor-shell/state-machine.js \
	dist/editor-shell/editor-session.js \
	dist/input/input-adapter.js dist/input/clipboard-adapter.js \
	dist/reader-shell/tile-scheduler.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# First gate for promoting range selection into the narrow contract.  Runs on
# the *already built* e1-editor-discovery profile: the whole point is to decide
# whether a rebuild of e1-editor-v1 is worth paying for, so it must not need one.
e1-drag-select-gate-assets: dist/e1-drag-select-gate.html \
	dist/e1-drag-select-gate-app.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Task #47 P1.  Runs against the FROZEN e1-editor-v1 and must never cause it to
# be rebuilt, so this depends on the page, the SDK and the fixtures -- and on no
# profile target at all.  finding 041: read the whole chain with `make -n`, not
# just this recipe, before believing that.
# Task #47 P2.  Runs against BOTH the archived e2-format-discovery (as the
# control that must still fail) and the new e2-combination, so it depends on
# neither profile target -- pointing --profile at a profile that has not been
# built is a runner error, not a reason to rebuild one.
f039-composition-scan-assets: dist/f039-composition-scan.html \
	dist/f039-composition-scan-app.js dist/sdk/document-sdk.js \
	dist/e2/format-discovery-client.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

f039-product-readback-assets: dist/f039-product-readback.html \
	dist/f039-product-readback-app.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

# Session-depth control ladder.  Deliberately depends on NO profile and no SDK:
# it exists to run the same navigation loop with the engine removed, so a wedge
# that reproduces here is not ours.
e1-c-session-depth-control-assets: dist/e1-c-session-depth-control.html \
	dist/e1-c-session-depth-control-app.js dist/e1-c-session-depth-worker.js \
	dist/e1-c-session-depth-engine-worker.js

# The `minimal` rung of the same ladder: a module with the engine's exact
# resource shape (link_r5_product's flags minus LibreOffice, its pre-js and its
# --wrap) and no LibreOffice code.  The `realinstant` rung needs no target of
# its own -- it runs against the already shipped e1-editor-v1 profile.
e1-c-session-depth-minimal-assets: e1-c-session-depth-control-assets \
	dist/e1-c-minimal/minimal.js dist/e1-c-minimal/minimal.wasm

E1_C_MINIMAL_BUILD := build/e1-c-session-depth-minimal

$(E1_C_MINIMAL_BUILD) dist/e1-c-minimal:
	mkdir -p $@

# Flags are link_r5_product verbatim, minus the LibreOffice objects/libs, the
# exports file, the two pre-js files and the --wrap; a wedge reproduced here is
# emscripten-runtime- or browser-shaped, not LibreOffice-shaped.
$(E1_C_MINIMAL_BUILD)/minimal.js: src/session_depth_minimal.cpp Makefile | $(E1_C_MINIMAL_BUILD)
	$(CXX) $< \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sASSERTIONS=0 -sEXIT_RUNTIME=0 \
		-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPU8 \
		-sEXPORTED_FUNCTIONS=_oxsdk_minimal_ping \
		-o $@

$(E1_C_MINIMAL_BUILD)/minimal.wasm: $(E1_C_MINIMAL_BUILD)/minimal.js
	@test -s $@

dist/e1-c-minimal/minimal.js: $(E1_C_MINIMAL_BUILD)/minimal.js | dist/e1-c-minimal
	cp $< $@

dist/e1-c-minimal/minimal.wasm: $(E1_C_MINIMAL_BUILD)/minimal.wasm | dist/e1-c-minimal
	cp $< $@

# Finding 018 attribution on two *already built* diagnostic profiles.  No
# profile prerequisite: both e1-editor-discovery and e2-mainloop-attribution
# are already linked, and rebuilding either would change what is being compared.
f018-line-nav-assets: dist/f018-line-nav-check.html dist/f018-line-nav-app.js \
	dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e1-editor-validation-assets: e1-editor-assets \
	dist/e1-editor-validation.html dist/e1-editor-validation-app.js \
	dist/e1/editor-shell-bundle-v1.json \
	$(addprefix dist/r7-compat-fixtures/,$(R7_COMPAT_FILES))

finding-016-scheduler-assets: finding-016-scheduler-profile \
	dist/finding-016-scheduler.html dist/finding-016-scheduler-app.js \
	dist/e1/editor-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

finding-016-selection-barrier-assets: finding-016-selection-barrier-profile \
	dist/finding-016-selection-barrier.html \
	dist/finding-016-selection-barrier-app.js \
	dist/e1/editor-discovery-client.js dist/sdk/document-sdk.js \
	dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

finding-012-assets: r7-longevity-assets dist/r7-close-minimizer.html \
	dist/r7-close-minimizer-app.js \
	$(addprefix dist/r7-finding-012/,$(FINDING_012_FILES))

finding-012-attribution-assets: finding-012-assets \
	$(FINDING_012_BUILD)/native-lok-probe \
	$(FINDING_012_DIAGNOSTIC_DIST)/sdk-manifest.json

r7-remediation-assets: finding-012-assets dist/document-sdk.js \
	dist/document-sdk.d.ts dist/r7-close-minimizer-app.js

src/%.o: src/%.cpp $(HEADERS) Makefile
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -c $< -o $@

dist:
	mkdir -p $@

dist/provider-sdk dist/providers:
	mkdir -p $@

dist/r6-fixtures:
	mkdir -p $@

dist/profiles/writer-review-r6:
	mkdir -p $@

dist/reader-shell:
	mkdir -p $@

dist/collaboration:
	mkdir -p $@

dist/input dist/r7 dist/r8 dist/r8c dist/delivery dist/releases dist/r7-fixtures \
		dist/r7-compat-fixtures dist/r7-finding-012 dist/e1 dist/e1-fixtures \
		dist/sdk dist/editor-shell dist/e2:
	mkdir -p $@

dist/exports.txt: $(CORE_EXPORTS) Makefile | dist
	# The tail of the core list is bridge RTTI implemented only by libunoembind.a.
	# This probe excludes unoembind, so retain the fixed C exports and the one
	# file-load exception RTTI required below.
	grep -v '^__ZTI' $< > $@
	# Keep the file UCP exception RTTI canonical across static archives.  This one
	# is provided by the Writer linkdeps and is needed by documentLoad's catch.
	printf '%s\n' __ZTIN3com3sun4star3ucb31InteractiveAugmentedIOExceptionE >> $@
	printf '%s\n' \
		_probe_start \
		_probe_open \
		_probe_paint_tile \
		_probe_click \
		_probe_insert_text \
		_probe_key \
		_probe_save \
		_probe_close \
		_probe_free \
		_oxsdk_abi_version \
		_oxsdk_capabilities \
		_oxsdk_engine_start \
		_oxsdk_document_open \
		_oxsdk_document_paint \
		_oxsdk_document_click \
		_oxsdk_document_insert_text \
		_oxsdk_document_save \
		_oxsdk_document_close \
		_oxsdk_document_search \
		_oxsdk_document_get_selection \
		_oxsdk_document_replace_selection \
		_oxsdk_document_undo \
		_oxsdk_document_add_comment \
		_oxsdk_document_list_comments \
		_oxsdk_document_set_track_changes \
		_oxsdk_document_list_changes \
		_oxsdk_request_cancel \
		_oxsdk_buffer_alloc \
		_oxsdk_buffer_free >> $@

$(R5_BUILD)/writer-review $(R5_BUILD)/writer-reader:
	mkdir -p $@

$(FINDING_012_BUILD) $(FINDING_012_DIAGNOSTIC_BUILD) \
		$(FINDING_012_DIAGNOSTIC_DIST) $(E1_BUILD) $(E1_DIST) \
		$(E1_B_BUILD) $(E1_B_DIST) $(E1_FIX_BUILD) $(E1_FIX_DIST) \
		$(E2_B_BUILD) $(E2_B_DIST) \
		$(FINDING_016_SCHEDULER_BUILD) $(FINDING_016_SCHEDULER_DIST) \
		$(FINDING_016_SELECTION_BUILD) $(FINDING_016_SELECTION_DIST) \
		$(E2_BUILD) $(E2_DIST) $(E2_WAIT_BUILD) $(E2_WAIT_DIST) \
		$(E2_PREGUARD_BUILD) $(E2_PREGUARD_DIST) \
		$(E2_COMBO_BUILD) $(E2_COMBO_DIST) \
		$(E2_SCHED_BUILD) $(E2_SCHED_DIST) \
		$(E2_MAINLOOP_BUILD) $(E2_MAINLOOP_DIST) \
		$(E2_MLPEI_BUILD) $(E2_MLPEI_DIST) \
		$(E2_LOCALE_BUILD) $(E2_LOCALE_DIST):
	mkdir -p $@

$(R5_BUILD)/writer-review/%.o: src/%.cpp $(HEADERS) Makefile | $(R5_BUILD)/writer-review
	$(CXX) $(CPPFLAGS) $(R5_CXXFLAGS) -c $< -o $@

$(R5_BUILD)/writer-reader/%.o: src/%.cpp $(HEADERS) Makefile | $(R5_BUILD)/writer-reader
	$(CXX) $(CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_READER_PROFILE -c $< -o $@

$(FINDING_012_DIAGNOSTIC_BUILD)/%.o: src/%.cpp $(HEADERS) Makefile | $(FINDING_012_DIAGNOSTIC_BUILD)
	$(CXX) $(CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_DIAGNOSTIC_CLOSE_STAGES -c $< -o $@

$(E1_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E1_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -c $< -o $@

$(E1_B_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h Makefile | $(E1_B_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -c $< -o $@

$(E1_FIX_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h Makefile | $(E1_FIX_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -c $< -o $@

$(E2_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-c $< -o $@

$(E2_WAIT_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_WAIT_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-c $< -o $@

$(E2_WAIT_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_WAIT_BUILD)
	cp $< $@

$(E2_WAIT_BUILD)/probe.js: $(E2_WAIT_OBJECTS) $(E2_WAIT_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_e2_wait_diagnostic,$(E2_WAIT_OBJECTS),$(E2_WAIT_BUILD)/exports.txt,$@)

$(E2_WAIT_BUILD)/probe.wasm: $(E2_WAIT_BUILD)/probe.js
	@test -s $@

$(E2_WAIT_DIST)/sdk-manifest.json: $(E2_WAIT_BUILD)/probe.js \
		$(E2_WAIT_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_WAIT_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_WAIT_BUILD)/probe.js --wasm $(E2_WAIT_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_WAIT_DIST) \
		--profile-name e2-wait-diagnostic --lok-trace
	@test -s $(E2_WAIT_DIST)/probe.js
	@test -s $(E2_WAIT_DIST)/probe.wasm
	@test -s $(E2_WAIT_DIST)/sdk-worker.js

e2-wait-diagnostic-profile: $(E2_WAIT_DIST)/sdk-manifest.json

$(E2_PREGUARD_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_PREGUARD_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_037_GUARD_OFF \
		-c $< -o $@

$(E2_PREGUARD_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_PREGUARD_BUILD)
	cp $< $@

$(E2_PREGUARD_BUILD)/probe.js: $(E2_PREGUARD_OBJECTS) $(E2_PREGUARD_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_e2_preguard_profiling,$(E2_PREGUARD_OBJECTS),$(E2_PREGUARD_BUILD)/exports.txt,$@)

$(E2_PREGUARD_BUILD)/probe.wasm: $(E2_PREGUARD_BUILD)/probe.js
	@test -s $@

$(E2_PREGUARD_DIST)/sdk-manifest.json: $(E2_PREGUARD_BUILD)/probe.js \
		$(E2_PREGUARD_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_PREGUARD_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_PREGUARD_BUILD)/probe.js --wasm $(E2_PREGUARD_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_PREGUARD_DIST) \
		--profile-name e2-preguard-profiling --lok-trace
	@test -s $(E2_PREGUARD_DIST)/probe.js
	@test -s $(E2_PREGUARD_DIST)/probe.wasm
	@test -s $(E2_PREGUARD_DIST)/sdk-worker.js

$(E2_COMBO_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
		src/editor_discovery_api.h Makefile | $(E2_COMBO_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-c $< -o $@

# The union of both export lists, written out rather than copied from either
# side: copying one and appending the other would hide which symbols this
# artifact is actually meant to expose.
$(E2_COMBO_BUILD)/exports.txt: $(R5_BUILD)/writer-review/exports.txt Makefile \
		| $(E2_COMBO_BUILD)
	cp $< $@
	printf '%s\n' \
		_oxsdk_editor_action \
		_oxsdk_editor_get_state \
		_oxsdk_editor_select_range \
		_oxsdk_editor_discovery_action \
		_oxsdk_editor_discovery_select \
		_oxsdk_editor_discovery_get_state >> $@

$(E2_COMBO_BUILD)/probe.js: $(E2_COMBO_OBJECTS) $(E2_COMBO_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,e2-combination 940b7723 -- the #49 fix, the SPEC E2-B section 3 gate (both rounds) and every cross-paragraph record bind to it)
	$(call link_r5_product,$(E2_COMBO_OBJECTS),$(E2_COMBO_BUILD)/exports.txt,$@)

$(E2_COMBO_BUILD)/probe.wasm: $(E2_COMBO_BUILD)/probe.js
	@test -s $@

# narrow-editor-v1 has to be declared as well, or sdk-worker.js refuses every
# product-ABI method on this profile and the combination could not be driven at
# all -- the capability gate is the worker's, not the engine's.
$(E2_COMBO_DIST)/sdk-manifest.json: $(E2_COMBO_BUILD)/probe.js \
		$(E2_COMBO_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_COMBO_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_COMBO_BUILD)/probe.js --wasm $(E2_COMBO_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_COMBO_DIST) \
		--profile-name e2-combination --extra-capability narrow-editor-v1
	@test -s $(E2_COMBO_DIST)/probe.js
	@test -s $(E2_COMBO_DIST)/probe.wasm
	@test -s $(E2_COMBO_DIST)/sdk-worker.js
	@grep -q narrow-editor-v1 $(E2_COMBO_DIST)/sdk-manifest.json
	@grep -q editor-discovery-closed-actions $(E2_COMBO_DIST)/sdk-manifest.json
	# The capability alone does not open the gate: sdk-worker.js also requires
	# editorContract.version === 1, and the first build of this profile shipped
	# without it and refused every product method at 0 ms.
	@python3 -c "import json,sys; m=json.load(open('$(E2_COMBO_DIST)/sdk-manifest.json')); sys.exit(0 if m.get('editorContract',{}).get('version')==1 else 1)"

e2-combination-profile: $(E2_COMBO_DIST)/sdk-manifest.json

e2-preguard-profiling-profile: $(E2_PREGUARD_DIST)/sdk-manifest.json

e2-preguard-profiling-assets: e2-preguard-profiling-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/e2/discovery-matrix-v1.json \
	dist/sdk/document-sdk.js dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

e2-wait-diagnostic-assets: e2-wait-diagnostic-profile \
	dist/e2-format-discovery.html dist/e2-format-discovery-app.js \
	dist/e2/format-discovery-client.js dist/e2/discovery-matrix-v1.json \
	dist/sdk/document-sdk.js dist/e1-fixtures/manifest.json \
	$(addprefix dist/e1-fixtures/,$(E1_FIXTURE_FILES))

$(E2_SCHED_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_SCHED_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_FINDING_016_SCHEDULER_PROBE -c $< -o $@

$(E2_LOCALE_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_LOCALE_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_FINDING_016_SCHEDULER_PROBE \
		-DOXSDK_E2_UI_LANGUAGE='"$(E2_LOCALE_LANGUAGE)"' -c $< -o $@

$(E2_MAINLOOP_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_MAINLOOP_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_MAINLOOP_ENGINE -c $< -o $@

$(E2_MLPEI_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(E2_MLPEI_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-DOXSDK_MAINLOOP_ENGINE -DOXSDK_FINDING_016_SCHEDULER_PROBE -c $< -o $@

$(FINDING_016_SCHEDULER_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(FINDING_016_SCHEDULER_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SCHEDULER_PROBE -c $< -o $@

$(FINDING_016_SELECTION_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_discovery_api.h Makefile | $(FINDING_016_SELECTION_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -c $< -o $@

$(R5_BUILD)/writer-review/exports.txt: $(CORE_EXPORTS) Makefile | $(R5_BUILD)/writer-review
	grep -v -e '^__ZTI' -e '^_main$$' $< > $@
	printf '%s\n' __ZTIN3com3sun4star3ucb31InteractiveAugmentedIOExceptionE >> $@
	printf '%s\n' \
		_oxsdk_abi_version \
		_oxsdk_capabilities \
		_oxsdk_engine_start \
		_oxsdk_document_open \
		_oxsdk_document_paint \
		_oxsdk_document_click \
		_oxsdk_document_insert_text \
		_oxsdk_document_save \
		_oxsdk_document_close \
		_oxsdk_document_search \
		_oxsdk_document_get_selection \
		_oxsdk_document_replace_selection \
		_oxsdk_document_undo \
		_oxsdk_document_add_comment \
		_oxsdk_document_list_comments \
		_oxsdk_document_set_track_changes \
		_oxsdk_document_list_changes \
		_oxsdk_request_cancel \
		_oxsdk_buffer_alloc \
		_oxsdk_buffer_free >> $@

$(R5_BUILD)/writer-reader/exports.txt: $(CORE_EXPORTS) Makefile | $(R5_BUILD)/writer-reader
	grep -v -e '^__ZTI' -e '^_main$$' $< > $@
	printf '%s\n' __ZTIN3com3sun4star3ucb31InteractiveAugmentedIOExceptionE >> $@
	printf '%s\n' \
		_oxsdk_abi_version \
		_oxsdk_capabilities \
		_oxsdk_engine_start \
		_oxsdk_document_open \
		_oxsdk_document_paint \
		_oxsdk_document_save \
		_oxsdk_document_close \
		_oxsdk_document_search \
		_oxsdk_request_cancel \
		_oxsdk_buffer_alloc \
		_oxsdk_buffer_free >> $@

define link_r5_product
	$(CXX) $(1) \
		-L$(LOBUILD)/instdir/program $$(cat $(LINKDEPS)) \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sASSERTIONS=0 -sEXIT_RUNTIME=0 \
		-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPU8 \
		-sEXPORTED_FUNCTIONS=@$(2) \
		-Wl,--wrap=_Z18initJsUnoScriptingv \
		--pre-js $(LOSRC)/static/emscripten/environment.js \
		--pre-js $(FS_PRE_JS) \
		-o $(3)
endef

# Finding 037 / 032.  The stuck thread is parked, not spinning (measured: a CPU
# profile during the hang is identical to one taken before it), so profiling is
# exhausted and the question is what it is waiting for.  Emscripten already
# knows how to answer that -- PTHREADS_DEBUG is a link-time setting that traces
# futex waits, mailbox activity and calls proxied to the main thread, which are
# exactly the three ways a thread can park here.
#
# Link-level only: no core change, no engine source change, and its own build
# and dist directories.  The shipped e2-format-discovery must not be rebuilt --
# A3/A4/A5 are bound to c89f069e and a rebuild unbinds all three (finding 027,
# finding 036).
#
# --profiling-funcs keeps the function names, so the trace names functions
# instead of wasm-function[36295].  ASSERTIONS=1 turns on a second batch of
# pthread checks that share the same #if.
# Relinking a frozen profile is never incidental.  The wasm hash is not a
# function of the source (finding 036) and every verdict binds to the artifact
# it was measured on (finding 027), so a new link silently invalidates whatever
# that profile carries.  The way it happens is never "someone decided to": it is
# a Makefile edit for an unrelated profile making these targets out of date.
#
#   $(1)  what the profile carries, for the message
define refuse_unasked_relink
	@if [ "$(ALLOW_FROZEN_RELINK)" != "1" ]; then \
		echo ""; \
		echo "refusing to relink a frozen profile: $@"; \
		echo "it carries: $(1)"; \
		echo "a new link mints a new artifact and unbinds that (findings 027, 036)."; \
		echo "if that is really what you want:  make ALLOW_FROZEN_RELINK=1 $@"; \
		echo ""; \
		exit 1; \
	fi
endef

define link_e2_wait_diagnostic
	$(CXX) $(1) \
		-L$(LOBUILD)/instdir/program $$(cat $(LINKDEPS)) \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sEXIT_RUNTIME=0 \
		-sPTHREADS_DEBUG=1 -sASSERTIONS=1 --profiling-funcs \
		-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPU8 \
		-sEXPORTED_FUNCTIONS=@$(2) \
		-Wl,--wrap=_Z18initJsUnoScriptingv \
		--pre-js $(LOSRC)/static/emscripten/environment.js \
		--pre-js $(FS_PRE_JS) \
		-o $(3)
endef

define link_e2_preguard_profiling
	$(CXX) $(1) \
		-L$(LOBUILD)/instdir/program $$(cat $(LINKDEPS)) \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --no-entry -Oz \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sEXIT_RUNTIME=0 \
		--profiling-funcs \
		-sEXPORTED_RUNTIME_METHODS=ccall,FS,HEAPU8 \
		-sEXPORTED_FUNCTIONS=@$(2) \
		-Wl,--wrap=_Z18initJsUnoScriptingv \
		--pre-js $(LOSRC)/static/emscripten/environment.js \
		--pre-js $(FS_PRE_JS) \
		-o $(3)
endef

$(R5_BUILD)/writer-review/probe.js: $(R5_REVIEW_OBJECTS) \
		$(R5_BUILD)/writer-review/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(R5_REVIEW_OBJECTS),$(R5_BUILD)/writer-review/exports.txt,$@)

$(R5_BUILD)/writer-review/probe.wasm: $(R5_BUILD)/writer-review/probe.js
	@test -s $@

$(R5_BUILD)/writer-reader/probe.js: $(R5_READER_OBJECTS) \
		$(R5_BUILD)/writer-reader/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(R5_READER_OBJECTS),$(R5_BUILD)/writer-reader/exports.txt,$@)

$(R5_BUILD)/writer-reader/probe.wasm: $(R5_BUILD)/writer-reader/probe.js
	@test -s $@

$(FINDING_012_DIAGNOSTIC_BUILD)/exports.txt: Makefile | $(FINDING_012_DIAGNOSTIC_BUILD)
	@test -s $(R5_BUILD)/writer-review/exports.txt
	cp $(R5_BUILD)/writer-review/exports.txt $@

$(FINDING_012_DIAGNOSTIC_BUILD)/probe.js: $(FINDING_012_DIAGNOSTIC_OBJECTS) \
		$(FINDING_012_DIAGNOSTIC_BUILD)/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(FINDING_012_DIAGNOSTIC_OBJECTS),$(FINDING_012_DIAGNOSTIC_BUILD)/exports.txt,$@)

$(FINDING_012_DIAGNOSTIC_BUILD)/probe.wasm: $(FINDING_012_DIAGNOSTIC_BUILD)/probe.js
	@test -s $@

$(E1_BUILD)/exports.txt: $(R5_BUILD)/writer-review/exports.txt Makefile | $(E1_BUILD)
	cp $< $@
	printf '%s\n' \
		_oxsdk_editor_discovery_action \
		_oxsdk_editor_discovery_select \
		_oxsdk_editor_discovery_get_state >> $@

$(E1_BUILD)/probe.js: $(E1_OBJECTS) $(E1_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,the e1-editor-discovery artifact 679def61 that E1-A/E1-B evidence binds to)
	$(call link_r5_product,$(E1_OBJECTS),$(E1_BUILD)/exports.txt,$@)

$(E1_BUILD)/probe.wasm: $(E1_BUILD)/probe.js
	@test -s $@

$(E1_B_BUILD)/exports.txt: $(R5_BUILD)/writer-review/exports.txt Makefile | $(E1_B_BUILD)
	cp $< $@
	printf '%s\n' \
		_oxsdk_editor_action \
		_oxsdk_editor_get_state \
		_oxsdk_editor_select_range >> $@

$(E1_B_BUILD)/probe.js: $(E1_B_OBJECTS) $(E1_B_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,the SHIPPED editor artifact 835b453d and the E1_GO_ODT_EDITOR verdict)
	$(call link_r5_product,$(E1_B_OBJECTS),$(E1_B_BUILD)/exports.txt,$@)

$(E1_B_BUILD)/probe.wasm: $(E1_B_BUILD)/probe.js
	@test -s $@

$(E2_B_BUILD)/%.o: src/%.cpp $(HEADERS) src/editor_api.h \
		src/format_readback_text.hpp Makefile | $(E2_B_BUILD)
	$(CXX) $(E1_CPPFLAGS) $(R5_CXXFLAGS) -DOXSDK_EDITOR_DISCOVERY \
		-DOXSDK_FINDING_016_SELECTION_BARRIER -DOXSDK_E2_FORMAT_BARRIER \
		-c $< -o $@

# Product exports only.  Deliberately NOT copied from the combination build:
# that one appends three _oxsdk_editor_discovery_* symbols, and an artifact
# exporting the diagnostic ABI can never be the product one (SPEC E2-B 5.8,
# and validate_e1_b.py already refuses any export containing
# "editor_discovery").  Written out rather than derived so the list is
# readable as an inventory.
$(E2_B_BUILD)/exports.txt: $(R5_BUILD)/writer-review/exports.txt Makefile \
		| $(E2_B_BUILD)
	cp $< $@
	printf '%s\n' \
		_oxsdk_editor_action \
		_oxsdk_editor_get_state \
		_oxsdk_editor_select_range \
		_oxsdk_editor_abi_version \
		_oxsdk_editor_set_action_gestures >> $@
	@if grep -q editor_discovery $@; then \
		echo "product export list contains a discovery symbol"; exit 1; fi

# Guarded from the FIRST link, not from the first verdict.  The guard costs one
# explicit flag and buys the property that no v2 artifact ever appears by
# accident -- including the one that later gets bound to, which is exactly the
# artifact nobody remembers was minted incidentally.
$(E2_B_BUILD)/probe.js: $(E2_B_OBJECTS) $(E2_B_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,the E2-B product v2 artifact -- every link mints a new hash and the SPEC E2-B section 7 evidence binds to one)
	$(call link_r5_product,$(E2_B_OBJECTS),$(E2_B_BUILD)/exports.txt,$@)

$(E2_B_BUILD)/probe.wasm: $(E2_B_BUILD)/probe.js
	@test -s $@

# The v2 product profile.  --cross-paragraph selects disposition B' (dispatch
# and verify every block); without it the same artifact ships disposition A
# (refuse cross-paragraph before dispatch).  That the choice is a builder flag
# rather than a build flag is the point: it is decided AFTER the artifact
# exists, so the wasm-parity question can be measured before it is answered.
$(E2_B_DIST)/sdk-manifest.json: $(E2_B_BUILD)/probe.js $(E2_B_BUILD)/probe.wasm \
		$(E2_B_BUILD)/exports.txt sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_b_profile.py \
		tools/e1_support.py | $(E2_B_DIST)
	python3 tools/build_e2_b_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_B_BUILD)/probe.js --wasm $(E2_B_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --exports $(E2_B_BUILD)/exports.txt \
		--output $(E2_B_DIST) --cross-paragraph
	@test -s $(E2_B_DIST)/probe.js
	@test -s $(E2_B_DIST)/probe.wasm
	@test -s $(E2_B_DIST)/sdk-worker.js
	@grep -q narrow-editor-v2 $(E2_B_DIST)/sdk-manifest.json
	@if grep -q '"narrow-editor-v1"' $(E2_B_DIST)/sdk-manifest.json; then \
		echo "v2 profile must not declare narrow-editor-v1"; exit 1; fi

e2-editor-v2-profile: $(E2_B_DIST)/sdk-manifest.json

$(E1_FIX_BUILD)/exports.txt: $(E1_B_BUILD)/exports.txt Makefile | $(E1_FIX_BUILD)
	cp $< $@

$(E1_FIX_BUILD)/probe.js: $(E1_FIX_OBJECTS) $(E1_FIX_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(E1_FIX_OBJECTS),$(E1_FIX_BUILD)/exports.txt,$@)

$(E1_FIX_BUILD)/probe.wasm: $(E1_FIX_BUILD)/probe.js
	@test -s $@

$(E2_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_BUILD)
	cp $< $@

# Relinking this one is never incidental.  The wasm hash is not a function of
# the source (finding 036), so a new link is a new artifact, and every E2-A
# verdict is bound to the artifact it was measured on (finding 027) -- A3, A4
# and A5 all go back to NOT_RUN the moment this file changes, and the way that
# has happened before is a Makefile edit for some other profile making this
# target out of date.  So it has to be asked for:
#
#     make ALLOW_FROZEN_RELINK=1 e2-format-discovery-assets
#
# and then re-swept with tools/sweep_e2_a.py, which is 44 runs.
$(E2_BUILD)/probe.js: $(E2_OBJECTS) $(E2_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call refuse_unasked_relink,the shipped E2 engine c89f069e and the A3/A4/A5 verdicts -- re-sweep with tools/sweep_e2_a.py after)
	$(call link_r5_product,$(E2_OBJECTS),$(E2_BUILD)/exports.txt,$@)

$(E2_BUILD)/probe.wasm: $(E2_BUILD)/probe.js
	@test -s $@

$(E2_SCHED_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_SCHED_BUILD)
	cp $< $@
	printf '%s\n' _oxsdk_editor_discovery_drain_scheduler >> $@

$(E2_SCHED_BUILD)/probe.js: $(E2_SCHED_OBJECTS) $(E2_SCHED_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(E2_SCHED_OBJECTS),$(E2_SCHED_BUILD)/exports.txt,$@)

$(E2_SCHED_BUILD)/probe.wasm: $(E2_SCHED_BUILD)/probe.js
	@test -s $@

$(E2_LOCALE_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_LOCALE_BUILD)
	cp $< $@
	printf '%s\n' _oxsdk_editor_discovery_drain_scheduler >> $@

$(E2_LOCALE_BUILD)/probe.js: $(E2_LOCALE_OBJECTS) $(E2_LOCALE_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(E2_LOCALE_OBJECTS),$(E2_LOCALE_BUILD)/exports.txt,$@)

$(E2_LOCALE_BUILD)/probe.wasm: $(E2_LOCALE_BUILD)/probe.js
	@test -s $@

$(E2_MAINLOOP_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_MAINLOOP_BUILD)
	cp $< $@

$(E2_MLPEI_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(E2_MLPEI_BUILD)
	cp $< $@
	printf '%s\n' _oxsdk_editor_discovery_drain_scheduler >> $@

$(E2_MLPEI_BUILD)/probe.js: $(E2_MLPEI_OBJECTS) $(E2_MLPEI_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(E2_MLPEI_OBJECTS),$(E2_MLPEI_BUILD)/exports.txt,$@)

$(E2_MLPEI_BUILD)/probe.wasm: $(E2_MLPEI_BUILD)/probe.js
	@test -s $@

$(E2_MAINLOOP_BUILD)/probe.js: $(E2_MAINLOOP_OBJECTS) $(E2_MAINLOOP_BUILD)/exports.txt \
		$(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(E2_MAINLOOP_OBJECTS),$(E2_MAINLOOP_BUILD)/exports.txt,$@)

$(E2_MAINLOOP_BUILD)/probe.wasm: $(E2_MAINLOOP_BUILD)/probe.js
	@test -s $@

$(FINDING_016_SCHEDULER_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(FINDING_016_SCHEDULER_BUILD)
	cp $< $@
	printf '%s\n' _oxsdk_editor_discovery_drain_scheduler >> $@

$(FINDING_016_SCHEDULER_BUILD)/probe.js: $(FINDING_016_SCHEDULER_OBJECTS) \
		$(FINDING_016_SCHEDULER_BUILD)/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(FINDING_016_SCHEDULER_OBJECTS),$(FINDING_016_SCHEDULER_BUILD)/exports.txt,$@)

$(FINDING_016_SCHEDULER_BUILD)/probe.wasm: $(FINDING_016_SCHEDULER_BUILD)/probe.js
	@test -s $@

$(FINDING_016_SELECTION_BUILD)/exports.txt: $(E1_BUILD)/exports.txt Makefile | $(FINDING_016_SELECTION_BUILD)
	cp $< $@

$(FINDING_016_SELECTION_BUILD)/probe.js: $(FINDING_016_SELECTION_OBJECTS) \
		$(FINDING_016_SELECTION_BUILD)/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(call link_r5_product,$(FINDING_016_SELECTION_OBJECTS),$(FINDING_016_SELECTION_BUILD)/exports.txt,$@)

$(FINDING_016_SELECTION_BUILD)/probe.wasm: $(FINDING_016_SELECTION_BUILD)/probe.js
	@test -s $@

$(E1_DIST)/sdk-manifest.json: $(E1_BUILD)/probe.js \
		$(E1_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e1_discovery_profile.py \
		tools/e1_support.py | $(E1_DIST)
	python3 tools/build_e1_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E1_BUILD)/probe.js --wasm $(E1_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E1_DIST)
	@test -s $(E1_DIST)/probe.js
	@test -s $(E1_DIST)/probe.wasm
	@test -s $(E1_DIST)/sdk-worker.js

e1-discovery-profile: $(E1_DIST)/sdk-manifest.json

$(E1_B_DIST)/sdk-manifest.json: $(E1_B_BUILD)/probe.js \
		$(E1_B_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e1_b_profile.py \
		tools/e1_support.py | $(E1_B_DIST)
	python3 tools/build_e1_b_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E1_B_BUILD)/probe.js --wasm $(E1_B_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E1_B_DIST)
	@test -s $(E1_B_DIST)/probe.js
	@test -s $(E1_B_DIST)/probe.wasm
	@test -s $(E1_B_DIST)/sdk-worker.js

e1-editor-profile: $(E1_B_DIST)/sdk-manifest.json

$(E1_FIX_DIST)/sdk-manifest.json: $(E1_FIX_BUILD)/probe.js \
		$(E1_FIX_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e1_b_profile.py \
		tools/e1_support.py | $(E1_FIX_DIST)
	python3 tools/build_e1_b_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E1_FIX_BUILD)/probe.js --wasm $(E1_FIX_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E1_FIX_DIST)
	@test -s $(E1_FIX_DIST)/probe.js
	@test -s $(E1_FIX_DIST)/probe.wasm

e1-noopfix-profile: $(E1_FIX_DIST)/sdk-manifest.json

$(E2_DIST)/sdk-manifest.json: $(E2_BUILD)/probe.js \
		$(E2_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_BUILD)/probe.js --wasm $(E2_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_DIST)
	@test -s $(E2_DIST)/probe.js
	@test -s $(E2_DIST)/probe.wasm
	@test -s $(E2_DIST)/sdk-worker.js

e2-format-discovery-profile: $(E2_DIST)/sdk-manifest.json

$(E2_SCHED_DIST)/sdk-manifest.json: $(E2_SCHED_BUILD)/probe.js \
		$(E2_SCHED_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_SCHED_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_SCHED_BUILD)/probe.js --wasm $(E2_SCHED_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_SCHED_DIST) \
		--profile-name e2-scheduler-attribution \
		--scope e2-scheduler-attribution \
		--extra-capability finding-016-scheduler-probe
	@test -s $(E2_SCHED_DIST)/probe.js
	@test -s $(E2_SCHED_DIST)/probe.wasm
	@test -s $(E2_SCHED_DIST)/sdk-worker.js

e2-scheduler-attribution-profile: $(E2_SCHED_DIST)/sdk-manifest.json

$(E2_LOCALE_DIST)/sdk-manifest.json: $(E2_LOCALE_BUILD)/probe.js \
		$(E2_LOCALE_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_LOCALE_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_LOCALE_BUILD)/probe.js --wasm $(E2_LOCALE_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_LOCALE_DIST) \
		--profile-name e2-locale-attribution \
		--scope e2-locale-attribution \
		--extra-capability finding-016-scheduler-probe \
		--ui-language $(E2_LOCALE_LANGUAGE)
	@test -s $(E2_LOCALE_DIST)/probe.js
	@test -s $(E2_LOCALE_DIST)/probe.wasm
	@test -s $(E2_LOCALE_DIST)/sdk-worker.js

e2-locale-attribution-profile: $(E2_LOCALE_DIST)/sdk-manifest.json

$(E2_MAINLOOP_DIST)/sdk-manifest.json: $(E2_MAINLOOP_BUILD)/probe.js \
		$(E2_MAINLOOP_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_MAINLOOP_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_MAINLOOP_BUILD)/probe.js --wasm $(E2_MAINLOOP_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_MAINLOOP_DIST) \
		--profile-name e2-mainloop-attribution \
		--scope e2-mainloop-attribution \
		--extra-capability mainloop-engine
	@test -s $(E2_MAINLOOP_DIST)/probe.js
	@test -s $(E2_MAINLOOP_DIST)/probe.wasm
	@test -s $(E2_MAINLOOP_DIST)/sdk-worker.js

e2-mainloop-attribution-profile: $(E2_MAINLOOP_DIST)/sdk-manifest.json

$(E2_MLPEI_DIST)/sdk-manifest.json: $(E2_MLPEI_BUILD)/probe.js \
		$(E2_MLPEI_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json tools/build_e2_discovery_profile.py \
		tools/e1_support.py | $(E2_MLPEI_DIST)
	python3 tools/build_e2_discovery_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(E2_MLPEI_BUILD)/probe.js --wasm $(E2_MLPEI_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(E2_MLPEI_DIST) \
		--profile-name e2-mainloop-pei-attribution \
		--scope e2-mainloop-pei-attribution \
		--extra-capability mainloop-engine \
		--extra-capability finding-016-scheduler-probe
	@test -s $(E2_MLPEI_DIST)/probe.js
	@test -s $(E2_MLPEI_DIST)/probe.wasm
	@test -s $(E2_MLPEI_DIST)/sdk-worker.js

e2-mainloop-pei-attribution-profile: $(E2_MLPEI_DIST)/sdk-manifest.json

$(FINDING_016_SCHEDULER_DIST)/sdk-manifest.json: \
		$(FINDING_016_SCHEDULER_BUILD)/probe.js \
		$(FINDING_016_SCHEDULER_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json \
		tools/build_finding_016_scheduler_profile.py tools/e1_support.py | $(FINDING_016_SCHEDULER_DIST)
	python3 tools/build_finding_016_scheduler_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(FINDING_016_SCHEDULER_BUILD)/probe.js \
		--wasm $(FINDING_016_SCHEDULER_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(FINDING_016_SCHEDULER_DIST)
	@test -s $(FINDING_016_SCHEDULER_DIST)/probe.js
	@test -s $(FINDING_016_SCHEDULER_DIST)/probe.wasm
	@test -s $(FINDING_016_SCHEDULER_DIST)/sdk-worker.js

finding-016-scheduler-profile: $(FINDING_016_SCHEDULER_DIST)/sdk-manifest.json

$(FINDING_016_SELECTION_DIST)/sdk-manifest.json: \
		$(FINDING_016_SELECTION_BUILD)/probe.js \
		$(FINDING_016_SELECTION_BUILD)/probe.wasm sdk/sdk-worker.js \
		sdk/r6-writer-review-manifest.json \
		tools/build_finding_016_selection_barrier_profile.py tools/e1_support.py | $(FINDING_016_SELECTION_DIST)
	python3 tools/build_finding_016_selection_barrier_profile.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(FINDING_016_SELECTION_BUILD)/probe.js \
		--wasm $(FINDING_016_SELECTION_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js --output $(FINDING_016_SELECTION_DIST)
	@test -s $(FINDING_016_SELECTION_DIST)/probe.js
	@test -s $(FINDING_016_SELECTION_DIST)/probe.wasm
	@test -s $(FINDING_016_SELECTION_DIST)/sdk-worker.js

finding-016-selection-barrier-profile: $(FINDING_016_SELECTION_DIST)/sdk-manifest.json

$(FINDING_012_BUILD)/native-lok-probe: tools/finding_012_native_lok.cpp | $(FINDING_012_BUILD)
	$(HOST_CXX) -std=c++17 -O2 -I$(LOSRC)/include $< -ldl -o $@

$(FINDING_012_DIAGNOSTIC_DIST)/sdk-manifest.json: \
		$(FINDING_012_DIAGNOSTIC_BUILD)/probe.js \
		$(FINDING_012_DIAGNOSTIC_BUILD)/probe.wasm \
		sdk/sdk-worker.js sdk/r6-writer-review-manifest.json \
		tools/build_finding_012_diagnostic.py | $(FINDING_012_DIAGNOSTIC_DIST)
	python3 tools/build_finding_012_diagnostic.py \
		--source-manifest sdk/r6-writer-review-manifest.json \
		--loader $(FINDING_012_DIAGNOSTIC_BUILD)/probe.js \
		--wasm $(FINDING_012_DIAGNOSTIC_BUILD)/probe.wasm \
		--worker sdk/sdk-worker.js \
		--output $(FINDING_012_DIAGNOSTIC_DIST)
	@test -s $(FINDING_012_DIAGNOSTIC_DIST)/probe.js
	@test -s $(FINDING_012_DIAGNOSTIC_DIST)/probe.wasm
	@test -s $(FINDING_012_DIAGNOSTIC_DIST)/sdk-worker.js

dist/profiles/r5-inventory.json: dist/probe.js dist/probe.wasm \
		$(R5_BUILD)/writer-review/probe.js $(R5_BUILD)/writer-review/probe.wasm \
		$(R5_BUILD)/writer-reader/probe.js $(R5_BUILD)/writer-reader/probe.wasm \
		$(CORE_DATA) $(CORE_METADATA) sdk/sdk-worker.js tools/build_r5_profiles.py
	python3 tools/build_r5_profiles.py \
		--full-loader dist/probe.js --full-wasm dist/probe.wasm \
		--review-loader $(R5_BUILD)/writer-review/probe.js \
		--review-wasm $(R5_BUILD)/writer-review/probe.wasm \
		--reader-loader $(R5_BUILD)/writer-reader/probe.js \
		--reader-wasm $(R5_BUILD)/writer-reader/probe.wasm \
		--data $(CORE_DATA) --metadata $(CORE_METADATA) \
		--worker sdk/sdk-worker.js --output dist/profiles \
		--core-commit $(CORE_COMMIT)

r5-profiles: dist/profiles/r5-inventory.json

dist/probe.js: $(OBJECTS) dist/exports.txt $(LINKDEPS) $(FS_PRE_JS) Makefile
	$(CXX) $(OBJECTS) \
		-L$(LOBUILD)/instdir/program $$(cat $(LINKDEPS)) \
		-pthread -fwasm-exceptions -sSUPPORT_LONGJMP=wasm --bind \
		-sMODULARIZE -sEXPORT_NAME=createProbeModule \
		-sTOTAL_MEMORY=1GB -sPTHREAD_POOL_SIZE=7 -sPTHREAD_POOL_SIZE_STRICT=0 \
		-sSTACK_SIZE=131072 -sDEFAULT_PTHREAD_STACK_SIZE=65536 \
		-sFORCE_FILESYSTEM=1 -sWASM_BIGINT=1 -sERROR_ON_UNDEFINED_SYMBOLS=1 -sFETCH=1 \
		-sASSERTIONS=1 -sEXIT_RUNTIME=0 \
		-sEXPORTED_RUNTIME_METHODS=ccall,cwrap,FS,UTF8ToString,stringToNewUTF8,HEAPU8,HEAPU16,HEAPU32,registerType,ClassHandle \
		-sEXPORTED_FUNCTIONS=@dist/exports.txt \
		-Wl,--wrap=_Z18initJsUnoScriptingv \
		--pre-js $(LOSRC)/static/emscripten/environment.js \
		--pre-js $(FS_PRE_JS) \
		--profiling-funcs \
		-o $@

dist/probe.wasm: dist/probe.js
	@test -s $@

dist/soffice.data: $(CORE_DATA) | dist
	cp $< $@

dist/soffice.data.js.metadata: $(CORE_METADATA) | dist
	cp $< $@

dist/index.html: web/index.html | dist
	cp $< $@

# Keep the generated Emscripten loader as dist/probe.js. The browser harness
# source is web/probe.js, but is copied under a collision-free runtime name.
dist/app.js: web/probe.js | dist
	cp $< $@

dist/r2.html: web/r2.html | dist
	cp $< $@

dist/r2-app.js: web/r2-app.js | dist
	cp $< $@

dist/r3.html: web/r3.html | dist
	cp $< $@

dist/r3-app.js: web/r3-app.js | dist
	cp $< $@

dist/r4.html: web/r4.html | dist
	cp $< $@

dist/r4-app.js: web/r4-app.js | dist
	cp $< $@

dist/r5-reader.html: web/r5-reader.html | dist
	cp $< $@

dist/r5-reader-app.js: web/r5-reader-app.js | dist
	cp $< $@

dist/r6-discovery.html: web/r6-discovery.html | dist
	cp $< $@

dist/r6-discovery-app.js: web/r6-discovery-app.js | dist
	cp $< $@

dist/r7-discovery.html: web/r7-discovery.html | dist
	cp $< $@

dist/r7-discovery-app.js: web/r7-discovery-app.js | dist
	cp $< $@

dist/r7-reference.html: web/r7-reference.html | dist
	cp $< $@

dist/r7-reference-app.js: web/r7-reference-app.js | dist
	cp $< $@

dist/r7-compatibility.html: web/r7-compatibility.html | dist
	cp $< $@

dist/r7-compatibility-app.js: web/r7-compatibility-app.js | dist
	cp $< $@

dist/r7-longevity.html: web/r7-longevity.html | dist
	cp $< $@

dist/r7-longevity-app.js: web/r7-longevity-app.js | dist
	cp $< $@

dist/r7-close-minimizer.html: web/r7-close-minimizer.html | dist
	cp $< $@

dist/r7-close-minimizer-app.js: web/r7-close-minimizer-app.js | dist
	cp $< $@

dist/r8-discovery.html: web/r8-discovery.html | dist
	cp $< $@

dist/r8-discovery-app.js: web/r8-discovery-app.js | dist
	cp $< $@

dist/r8-discovery-sw.js: web/r8-discovery-sw.js | dist
	cp $< $@

dist/r8-delivery.html: web/r8-delivery.html | dist
	cp $< $@

dist/r8-delivery-app.js: web/r8-delivery-app.js | dist
	cp $< $@

dist/delivery/verified-loader.js: delivery/verified-loader.js | dist/delivery
	cp $< $@

dist/delivery/verified-loader.d.ts: delivery/verified-loader.d.ts | dist/delivery
	cp $< $@

dist/delivery/release-state.js: delivery/release-state.js | dist/delivery
	cp $< $@

dist/delivery/release-state.d.ts: delivery/release-state.d.ts | dist/delivery
	cp $< $@

dist/r8-update.html: web/r8-update.html | dist
	cp $< $@

dist/r8-update-app.js: web/r8-update-app.js | dist
	cp $< $@

dist/e1-discovery.html: web/e1-discovery.html | dist
	cp $< $@

dist/e1-discovery-app.js: web/e1-discovery-app.js | dist
	cp $< $@

dist/e1-manual-delete.html: web/e1-manual-delete.html | dist
	cp $< $@

dist/e1-manual-delete-app.js: web/e1-manual-delete-app.js | dist
	cp $< $@

dist/e1-editor.html: web/e1-editor.html | dist
	cp $< $@

dist/e1-editor-app.js: web/e1-editor-app.js | dist
	cp $< $@

dist/e1-c-session-depth-control.html: web/e1-c-session-depth-control.html | dist
	cp $< $@

dist/e1-c-session-depth-control-app.js: web/e1-c-session-depth-control-app.js | dist
	cp $< $@

dist/e1-c-session-depth-worker.js: web/e1-c-session-depth-worker.js | dist
	cp $< $@

dist/e1-c-session-depth-engine-worker.js: web/e1-c-session-depth-engine-worker.js | dist
	cp $< $@

dist/e1-drag-select-gate.html: web/e1-drag-select-gate.html | dist
	cp $< $@

dist/e1-drag-select-gate-app.js: web/e1-drag-select-gate-app.js | dist
	cp $< $@

dist/f039-composition-scan.html: web/f039-composition-scan.html | dist
	cp $< $@

dist/f039-composition-scan-app.js: web/f039-composition-scan-app.js | dist
	cp $< $@

dist/f039-product-readback.html: web/f039-product-readback.html | dist
	cp $< $@

dist/f039-product-readback-app.js: web/f039-product-readback-app.js | dist
	cp $< $@

dist/e1-session-wedge-recovery.html: web/e1-session-wedge-recovery.html | dist
	cp $< $@

dist/e1-session-wedge-recovery-app.js: web/e1-session-wedge-recovery-app.js | dist
	cp $< $@

dist/e1-post-wedge-liveness.html: web/e1-post-wedge-liveness.html | dist
	cp $< $@

dist/e1-post-wedge-liveness-app.js: web/e1-post-wedge-liveness-app.js | dist
	cp $< $@

dist/e1-checkpoint-cost.html: web/e1-checkpoint-cost.html | dist
	cp $< $@

dist/e1-checkpoint-cost-app.js: web/e1-checkpoint-cost-app.js | dist
	cp $< $@

dist/f018-line-nav-check.html: web/f018-line-nav-check.html | dist
	cp $< $@

dist/f018-line-nav-app.js: web/f018-line-nav-app.js | dist
	cp $< $@

dist/demo-editor.html: web/demo-editor.html | dist
	cp $< $@

dist/demo-editor-app.js: web/demo-editor-app.js | dist
	cp $< $@

dist/e1-editor-validation.html: web/e1-editor-validation.html | dist
	cp $< $@

dist/e1-editor-validation-app.js: web/e1-editor-validation-app.js | dist
	cp $< $@

dist/e1/editor-shell-bundle-v1.json: e1/editor-shell-bundle-v1.json | dist/e1
	cp $< $@

dist/finding-016-scheduler.html: web/finding-016-scheduler.html | dist
	cp $< $@

dist/finding-016-scheduler-app.js: web/finding-016-scheduler-app.js | dist
	cp $< $@

dist/finding-016-selection-barrier.html: web/finding-016-selection-barrier.html | dist
	cp $< $@

dist/finding-016-selection-barrier-app.js: web/finding-016-selection-barrier-app.js | dist
	cp $< $@

dist/e1/editor-discovery-client.js: e1/editor-discovery-client.js | dist/e1
	cp $< $@

dist/e2/format-discovery-client.js: e2/format-discovery-client.js | dist/e2
	cp $< $@

dist/e2/demo-structure-client.js: e2/demo-structure-client.js | dist/e2
	cp $< $@

dist/e2/discovery-matrix-v1.json: e2/discovery-matrix-v1.json | dist/e2
	cp $< $@

dist/e1-bold-noop-check.html: web/e1-bold-noop-check.html | dist
	cp $< $@

dist/e1-bold-noop-app.js: web/e1-bold-noop-app.js | dist
	cp $< $@

dist/demo-structure.html: web/demo-structure.html | dist
	cp $< $@

dist/f039-caret-reset-repro.html: web/f039-caret-reset-repro.html | dist
	cp $< $@

dist/f039-caret-reset-repro-app.js: web/f039-caret-reset-repro-app.js | dist
	cp $< $@

dist/demo-structure-app.js: web/demo-structure-app.js | dist
	cp $< $@

dist/e2-format-discovery.html: web/e2-format-discovery.html | dist
	cp $< $@

dist/e2-format-discovery-app.js: web/e2-format-discovery-app.js | dist
	cp $< $@

dist/editor-shell/editor-client.js: editor-shell/editor-client.js | dist/editor-shell
	cp $< $@

dist/editor-shell/editor-client.d.ts: editor-shell/editor-client.d.ts | dist/editor-shell
	cp $< $@

dist/editor-shell/state-machine.js: editor-shell/state-machine.js | dist/editor-shell
	cp $< $@

dist/editor-shell/editor-session.js: editor-shell/editor-session.js | dist/editor-shell
	cp $< $@

dist/editor-shell/recovery-notice.js: editor-shell/recovery-notice.js | dist/editor-shell
	cp $< $@

dist/sdk/document-sdk.js: sdk/document-sdk.js | dist/sdk
	cp $< $@

dist/r8-service-worker.js: web/r8-service-worker.js | dist
	cp $< $@

dist/r8/release-schema-v1.json: r8/release-schema-v1.json | dist/r8
	cp $< $@

dist/r8/release-manifest.json: r7-assets r8/release-schema-v1.json \
		tools/r8_release.py tools/build_r8_release_manifest.py | dist/r8
	python3 tools/build_r8_release_manifest.py --output $@

dist/releases/index.json: dist/r8/release-manifest.json tools/r8_bundle.py \
		tools/build_r8_bundles.py | dist/releases
	python3 tools/build_r8_bundles.py --output dist/releases

dist/r8c/release-set.json: dist/releases/index.json tools/r8_bundle.py \
		tools/build_r8_c_release_set.py | dist/r8c
	python3 tools/build_r8_c_release_set.py --output dist/r8c

dist/r7.css: web/r7.css | dist
	cp $< $@

dist/input/input-adapter.js: input/input-adapter.js | dist/input
	cp $< $@

dist/input/clipboard-adapter.js: input/clipboard-adapter.js | dist/input
	cp $< $@

dist/r7/page-navigation.js: r7/page-navigation.js | dist/r7
	cp $< $@

dist/r7/document-preflight.js: r7/document-preflight.js | dist/r7
	cp $< $@

dist/r7-fixtures/%: test-docs/r7/% | dist/r7-fixtures
	cp $< $@

dist/r7-compat-fixtures/%: test-docs/r7-compat/% | dist/r7-compat-fixtures
	cp $< $@

dist/r7-finding-012/%: test-docs/r7-finding-012/% | dist/r7-finding-012
	cp $< $@

test-docs/e1/manifest.json: tools/create_e1_corpus.py tools/e1_support.py
	python3 tools/create_e1_corpus.py

dist/e1-fixtures/manifest.json: test-docs/e1/manifest.json | dist/e1-fixtures
	cp $< $@

dist/e1-fixtures/%.odt: test-docs/e1/%.odt | dist/e1-fixtures
	cp $< $@

dist/r6-reader.html: web/r6-reader.html | dist
	cp $< $@

dist/r6-reader-app.js: web/r6-reader-app.js | dist
	cp $< $@

dist/r6-reference.html: web/r6-reference.html | dist
	cp $< $@

dist/r6-reference-app.js: web/r6-reference-app.js | dist
	cp $< $@

dist/r6.css: web/r6.css | dist
	cp $< $@

dist/reader-shell/%.js: reader-shell/%.js | dist/reader-shell
	cp $< $@

dist/collaboration/%.js: collaboration/%.js | dist/collaboration
	cp $< $@

dist/collaboration/%.d.ts: collaboration/%.d.ts | dist/collaboration
	cp $< $@

dist/profiles/writer-review-r6/sdk-worker.js: sdk/sdk-worker.js | dist/profiles/writer-review-r6
	cp $< $@

dist/profiles/writer-review-r6/sdk-manifest.json: sdk/r6-writer-review-manifest.json | dist/profiles/writer-review-r6
	cp $< $@

dist/r6-fixtures/%.odt: test-docs/%.odt | dist/r6-fixtures
	cp $< $@

dist/document-sdk.js: sdk/document-sdk.js | dist
	cp $< $@

dist/document-sdk.d.ts: sdk/document-sdk.d.ts | dist
	cp $< $@

dist/sdk-worker.js: sdk/sdk-worker.js | dist
	cp $< $@

dist/sdk-manifest.json: sdk/manifest.json | dist
	cp $< $@

dist/provider-sdk/provider-sdk.js: provider-sdk/provider-sdk.js | dist/provider-sdk
	cp $< $@

dist/provider-sdk/provider-sdk.d.ts: provider-sdk/provider-sdk.d.ts | dist/provider-sdk
	cp $< $@

dist/providers/text-translate-descriptor.js: providers/text-translate-descriptor.js | dist/providers
	cp $< $@

dist/providers/text-translate-provider.js: providers/text-translate-provider.js | dist/providers
	cp $< $@

dist/providers/text-translate-worker.js: providers/text-translate-worker.js | dist/providers
	cp $< $@

serve: all
	python3 web/serve.py

serve-r5: r5
	python3 web/serve.py

# One command for the demo shell.  Copies the two presentation files and
# serves dist with the cross-origin isolation headers the engine needs; it does
# not build anything, so the frozen e1-editor-v1 artifact stays untouched.
serve-demo: demo-editor-assets
	@echo "開啟 http://127.0.0.1:8765/demo-editor.html"
	python3 web/serve.py

test-r2:
	node --test sdk/tests/*.test.mjs
	c++ -std=c++17 -Isrc -fsyntax-only tests/abi_header_test.cpp

test-r3: test-r2

test-r4: test-r3
	node --test provider-sdk/tests/*.test.mjs

test-r5: test-r4
	node --check sdk/sdk-worker.js
	python3 -m unittest tests/test_r5_profiles.py

test-r6-a:
	node --test reader-shell/tests/*.test.mjs
	node --check web/r6-discovery-app.js
	node --check web/r6-reader-app.js

test-r6-b: test-r6-a
	node --test collaboration/tests/*.test.mjs
	node --check collaboration/contract.js
	node --check collaboration/domain.js
	node --check collaboration/reference-service.js

test-r6-c: test-r6-b
	node --check web/r6-reference-app.js
	node --check tools/serve_r6_reference.mjs

test-r6-roundtrip:
	python3 tools/validate_r6_roundtrip.py

test-r6-release:
	python3 tools/validate_r6_release.py

test-r7-a-static:
	node --test input/tests/input-adapter.test.mjs
	python3 -m unittest tests/test_r7_corpus.py
	node --check input/input-adapter.js
	node --check web/r7-discovery-app.js
	python3 -m py_compile tools/create_r7_corpus.py tools/validate_r7_corpus.py \
		tools/run_r7_discovery.py tools/validate_r7_a.py tools/validate_r7_preflight.py

test-r7-b-static:
	node --test input/tests/*.test.mjs
	node --test r7/tests/page-navigation.test.mjs
	node --check input/input-adapter.js
	node --check input/clipboard-adapter.js
	node --check web/r7-reference-app.js
	python3 -m py_compile tools/r7_support.py tools/run_r7_input.py tools/validate_r7_b.py

test-r7-c-static: test-r7-b-static
	node --test r7/tests/*.test.mjs
	python3 -m unittest tests/test_r7_compatibility_corpus.py
	node --check r7/document-preflight.js
	node --check web/r7-compatibility-app.js
	python3 -m py_compile tools/create_r7_compatibility_corpus.py \
		tools/validate_r7_compatibility_corpus.py tools/run_r7_compatibility.py \
		tools/validate_r7_c.py tests/test_r7_compatibility_corpus.py

test-r7-d-static: test-r7-c-static
	node --check web/r7-longevity-app.js
	python3 -m unittest tests/test_r7_longevity.py
	python3 -m py_compile tools/r7_longevity_analysis.py tools/run_r7_usability.py \
		tools/run_r7_longevity.py tools/validate_r7_d.py tests/test_r7_longevity.py

test-r8-a-static: r8-discovery-assets
	python3 -m unittest tests/test_r8_release.py \
		tests/test_r8_delivery_server.py tests/test_r8_a.py
	node --check web/r8-discovery-app.js
	node --check web/r8-discovery-sw.js
	python3 -m py_compile tools/r8_release.py tools/build_r8_release_manifest.py \
		tools/r8_delivery_server.py tools/run_r8_discovery.py \
		tools/validate_r8_a.py tools/validate_r8_preflight.py \
		tests/test_r8_release.py tests/test_r8_delivery_server.py tests/test_r8_a.py

test-r8-b-static: r8-delivery-assets
	python3 -m unittest tests/test_r8_bundle.py tests/test_r8_delivery_server.py
	python3 -m unittest tests/test_r8_b.py
	node --test delivery/tests/verified-loader.test.mjs
	node --check delivery/verified-loader.js
	node --check web/r8-delivery-app.js
	python3 -m py_compile tools/r8_bundle.py tools/build_r8_bundles.py \
		tools/r8_delivery_server.py tools/run_r8_delivery.py \
		tools/validate_r8_b_preflight.py tools/validate_r8_b_roundtrip.py \
		tools/validate_r8_b.py tests/test_r8_bundle.py \
		tests/test_r8_delivery_server.py tests/test_r8_b.py

# No asset prerequisite, on purpose (SPEC-E1-C v9, finding 041).  That
# prerequisite reached a .PHONY chain ending in build_r8_release_manifest.py
# and build_r8_bundles.py, so running this *test* target minted an R8 release
# id as a side effect -- and E1-C's regression property runs it, meaning
# validate_e1_c.py --run-regression minted one on every invocation.  Minting
# was never an assertion here; it was routing.  The recipe is unchanged.
test-r8-c-static:
	python3 -m unittest tests/test_r8_bundle.py tests/test_r8_c.py
	node --test delivery/tests/verified-loader.test.mjs \
		delivery/tests/release-state.test.mjs
	node --check web/r8-service-worker.js
	node --check web/r8-update-app.js
	python3 -m py_compile tools/build_r8_c_release_set.py \
		tools/run_r8_service_worker.py tools/validate_r8_c_preflight.py \
		tools/validate_r8_c.py tests/test_r8_c.py

test-r8-d-static: test-r8-c-static
	python3 -m unittest tests/test_r8_d.py
	python3 -m json.tool r8/production-matrix-v1.json >/dev/null
	python3 -m py_compile tools/run_r8_production.py tools/validate_r8_d.py \
		tests/test_r8_d.py

test-e1-a-static:
	python3 -m unittest tests/test_e1_corpus.py \
		tests/test_e1_discovery_profile.py tests/test_e1_a.py \
		tests/test_content_axis_inventory.py \
		tests/test_finding_016_remediation.py
	node --test e1/tests/editor-discovery-client.test.mjs \
		sdk/tests/document-sdk.test.mjs
	node --check e1/editor-discovery-client.js
	node --check sdk/sdk-worker.js
	node --check web/e1-discovery-app.js
	node --check web/e1-manual-delete-app.js
	python3 -m json.tool e1/discovery-matrix-v1.json >/dev/null
	c++ -std=c++17 -Isrc -fsyntax-only tests/editor_discovery_abi_header_test.cpp
	python3 tools/validate_e1_corpus.py
	python3 -m json.tool e1/content-axis-suites.json >/dev/null
	python3 tools/inventory_corpus_axes.py --check
	python3 -m py_compile tools/e1_support.py \
		tools/build_e1_discovery_profile.py tools/create_e1_corpus.py \
		tools/validate_e1_corpus.py tools/validate_e1_preflight.py \
		tools/run_e1_discovery.py tools/validate_e1_roundtrip.py \
		tools/validate_e1_a.py tools/validate_finding_016_remediation.py \
		tools/inventory_corpus_axes.py tools/run_e1_wedge_harness.py \
		tests/test_e1_corpus.py tests/test_e1_discovery_profile.py \
		tests/test_e1_a.py tests/test_content_axis_inventory.py \
		tests/test_finding_016_remediation.py

test-e1-b-static:
	python3 -m unittest tests/test_e1_b_profile.py tests/test_e1_b.py
	node --test editor-shell/tests/*.test.mjs sdk/tests/document-sdk.test.mjs \
		input/tests/input-adapter.test.mjs reader-shell/tests/tile-scheduler.test.mjs
	node --check sdk/sdk-worker.js
	node --check editor-shell/editor-client.js
	node --check editor-shell/state-machine.js
	node --check editor-shell/editor-session.js
	node --check editor-shell/recovery-notice.js
	node --check web/e1-editor-app.js
	# The demo shell ships from this tree and imports the same editor-shell
	# modules, so it belongs under the same gate as the harness that validated
	# them.  It was outside every static target until 2026-08-13.
	node --check web/demo-editor-app.js
	c++ -std=c++17 -Isrc -fsyntax-only tests/editor_abi_header_test.cpp
	python3 -m py_compile tools/build_e1_b_profile.py tools/run_e1_b.py \
		tools/validate_e1_b.py tests/test_e1_b_profile.py tests/test_e1_b.py

# SPEC E2-B.  No prerequisites, same reason as test-e2-a-static below: nothing
# here may touch an artifact.
#
# The two native probes were written outside every static target -- they compile
# standalone from their own runner scripts, which is why adding them here was
# deferred (finding 042: editing this file rebuilds, so the entry waited for a
# turn when the Makefile was being edited anyway).  Syntax-only: they link
# against LibreOfficeKit at run time, and this checks the source, not the link.
test-e2-b-static:
	c++ -std=c++17 -Isrc -o $(E2_B_TEXT_TEST_BIN) tests/format_readback_text_test.cpp
	$(E2_B_TEXT_TEST_BIN)
	c++ -std=c++17 -I../libreoffice-26-8/include -fsyntax-only \
		tools/f049_native_select_after_format.cpp
	c++ -std=c++17 -I../libreoffice-26-8/include -fsyntax-only \
		tools/e2b_native_crossparagraph.cpp
	node --check web/e2b-gate-app.js
	python3 -m py_compile tools/run_e2b_gate.py tools/analyze_e2b_gate.py \
		tools/analyze_e2b_crossparagraph.py tools/analyze_e2b_identity_gate.py \
		tools/create_e2b_fixtures.py tools/build_e2_b_profile.py
	python3 -m unittest tests/test_e2_b_profile.py

# No prerequisites on purpose.  test-e1-c-static pulls e1-editor-validation-assets
# and therefore rebuilds the frozen e1-editor-v1 profile; this target must stay
# runnable without touching any artifact.
test-e2-a-static:
	python3 -m unittest tests/test_e2_profile.py tests/test_e2_a_roundtrip.py
	node --test e2/tests/*.test.mjs
	node --check e2/format-discovery-client.js
	node --check e2/demo-structure-client.js
	node --check web/demo-structure-app.js
	node --check web/f039-caret-reset-repro-app.js
	node --check web/e2-format-discovery-app.js
	node --check sdk/sdk-worker.js
	python3 -m json.tool e2/discovery-matrix-v1.json >/dev/null
	python3 -m py_compile tools/build_e2_discovery_profile.py \
		tools/run_e2_discovery.py tools/analyze_e2_a_native_caret.py \
		tools/analyze_e2_a_native_reissue.py tools/validate_e2_a.py \
		tools/validate_e2_a_roundtrip.py \
		tests/test_e2_profile.py tests/test_e2_a_roundtrip.py
	bash -n tools/run_e2_a_native_caret.sh
	bash -n tools/run_f039_native.sh
	bash -n tools/run_e2_a_native_reissue.sh
	c++ -std=c++17 -fsyntax-only -I$(LOSRC)/include \
		tools/e2_a_native_caret_tracking.cpp
	c++ -std=c++17 -fsyntax-only -I$(LOSRC)/include \
		tools/e2_a_native_reissue.cpp
	c++ -std=c++17 -fsyntax-only -I$(LOSRC)/include \
		tools/f039_native_caret_reset.cpp

# No asset prerequisite, on purpose (SPEC-E1-C v9).  Pulling
# e1-editor-validation-assets made this target depend on the build tree's
# mtimes being self-consistent, and line 486 lists Makefile itself as a
# prerequisite of every object -- so any Makefile edit, including one that
# adds an unrelated copy rule, drove it into a relink the frozen guard must
# refuse.  While the artifact is frozen the only way to make it green was to
# relink the frozen artifact: the exact thing the guard exists to prevent.
# The recipe below is unchanged, byte for byte; only the dependency on build
# freshness is gone.  test-e1-c-frozen-guard replaces it with an assertion
# that can actually go red.
test-e1-c-static:
	python3 -m unittest tests/test_e1_c.py
	node --test editor-shell/tests/*.test.mjs sdk/tests/document-sdk.test.mjs \
		input/tests/*.test.mjs reader-shell/tests/tile-scheduler.test.mjs
	node --check editor-shell/editor-session.js
	node --check web/e1-editor-app.js
	node --check web/e1-editor-validation-app.js
	python3 -m json.tool e1/validation-matrix-v1.json >/dev/null
	python3 -m json.tool e1/validation-matrix-v2.json >/dev/null
	python3 -m json.tool e1/editor-shell-bundle-v1.json >/dev/null
	python3 -m py_compile tools/run_e1_c.py tools/validate_e1_c.py \
		tests/test_e1_c.py tools/regenerate_shell_bundle.py
	python3 tools/regenerate_shell_bundle.py

# The regenerate tool's own self-test.  Separate from test-e1-c-static because
# it copies the tree four times and runs the unit suite inside each copy, so it
# is slow -- but it is the only thing that checks the tool cannot quietly widen
# what the manifest covers.  No prerequisites on purpose: finding 041.
test-e1-c-shell-bundle-tool:
	python3 tools/regenerate_shell_bundle.py --self-test

# The guard has to be asserted, not assumed.  --always-make -n makes this
# independent of every mtime in the tree: it asks "if this were rebuilt right
# now, would the link be refused?" and fails if the answer is no.  Delete the
# guard and this goes red; that is the property the old asset dependency was
# accidentally standing in for, stated directly.
test-e1-c-frozen-guard:
	make --always-make -n build/e1/editor-v1/probe.js 2>&1 \
		| grep -q "refusing to relink a frozen profile"

test-finding-016-scheduler-static:
	python3 -m unittest tests/test_finding_016_scheduler.py
	node --test e1/tests/editor-discovery-client.test.mjs
	node --check sdk/sdk-worker.js
	node --check web/finding-016-scheduler-app.js
	python3 -m py_compile tools/build_finding_016_scheduler_profile.py \
		tools/run_finding_016_scheduler.py tests/test_finding_016_scheduler.py

test-finding-016-selection-barrier-static:
	python3 -m unittest tests/test_finding_016_selection_barrier.py
	node --test e1/tests/editor-discovery-client.test.mjs
	node --check sdk/sdk-worker.js
	node --check web/finding-016-selection-barrier-app.js
	python3 -m py_compile \
		tools/build_finding_016_selection_barrier_profile.py \
		tools/run_finding_016_selection_barrier.py \
		tools/validate_finding_016_selection_barrier.py \
		tests/test_finding_016_selection_barrier.py

test-finding-012-static: test-r7-d-static
	python3 -m unittest tests/test_finding_012_corpus.py
	node --check web/r7-close-minimizer-app.js
	python3 -m py_compile tools/create_finding_012_corpus.py \
		tools/run_finding_012.py tools/validate_finding_012.py \
		tests/test_finding_012_corpus.py

test-finding-012-attribution:
	python3 -m unittest tests/test_finding_012_attribution.py
	node --check web/r7-close-minimizer-app.js
	python3 -m py_compile tools/build_finding_012_diagnostic.py \
		tools/run_finding_012_attribution.py \
		tools/validate_finding_012_attribution.py \
		tests/test_finding_012_attribution.py

test-finding-012-native-26-8:
	python3 -m unittest tests/test_finding_012_native_26_8.py
	python3 -m py_compile tools/validate_finding_012_native_26_8.py \
		tests/test_finding_012_native_26_8.py

test-finding-012-remediation:
	node --test sdk/tests/document-sdk.test.mjs
	python3 -m unittest tests/test_finding_012_remediation.py
	node --check sdk/document-sdk.js
	node --check web/r7-close-minimizer-app.js
	python3 -m py_compile tools/run_finding_012_remediation.py \
		tools/validate_finding_012_remediation.py \
		tests/test_finding_012_remediation.py

clean:
	rm -f $(OBJECTS) dist/exports.txt dist/probe.js dist/probe.wasm \
		dist/probe.wasm.debug.wasm \
		dist/soffice.data dist/soffice.data.js.metadata dist/index.html dist/app.js \
	dist/r2.html dist/r2-app.js dist/document-sdk.js dist/document-sdk.d.ts \
	dist/r3.html dist/r3-app.js \
	dist/r4.html dist/r4-app.js \
	dist/r5-reader.html dist/r5-reader-app.js \
	dist/r8-discovery.html dist/r8-discovery-app.js dist/r8-discovery-sw.js \
	dist/r8/release-schema-v1.json dist/r8/release-manifest.json \
	dist/sdk-worker.js dist/sdk-manifest.json \
	dist/provider-sdk/provider-sdk.js dist/provider-sdk/provider-sdk.d.ts \
	dist/providers/text-translate-descriptor.js \
	dist/providers/text-translate-provider.js dist/providers/text-translate-worker.js
