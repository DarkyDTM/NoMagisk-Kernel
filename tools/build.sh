#!/bin/bash

set -euo pipefail

OUT_DIR="out"
DEFCONFIG="vanillaKernel-defconfig"
LOG_FILE="build.log"
THREADS=$(nproc --all)

RAW_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Route clang through ccache when it is available to speed up rebuilds
if command -v ccache >/dev/null 2>&1; then
    CC_WRAPPER="ccache "
else
    CC_WRAPPER=""
fi

case "$RAW_BRANCH" in
    lineage-23.2)      BRANCH="stable" ;;
    lineage-23.2-test) BRANCH="unstable" ;;
    *)                 BRANCH="unknown" ;;
esac

MAKE_FLAGS=(
    O="$OUT_DIR"
    ARCH=arm64
    LLVM=1
    LLVM_IAS=1
    CC="${CC_WRAPPER}clang"
    LD=ld.lld
    AR=llvm-ar
    NM=llvm-nm
    OBJCOPY=llvm-objcopy
    OBJDUMP=llvm-objdump
    STRIP=llvm-strip
    CLANG_TRIPLE=aarch64-linux-gnu-
    LOCALVERSION="-${BRANCH}-${COMMIT}"
)

usage() {
    echo "Usage: $0 <config [base_defconfig] [extra1.config ...] | kernel>"
    exit 1
}

if [ $# -eq 0 ]; then
    usage
fi

mkdir -p "$OUT_DIR"

case "$1" in
    config)
        shift
        if [ $# -gt 0 ]; then
            BASE_CONFIG="$1"
            shift
        else
            BASE_CONFIG="$DEFCONFIG"
        fi
        EXTRA_CONFIGS=("$@")

        if [ ! -f "arch/arm64/configs/$BASE_CONFIG" ]; then
            echo "Error: Base config arch/arm64/configs/$BASE_CONFIG not found!"
            exit 1
        fi

        if [ ${#EXTRA_CONFIGS[@]} -eq 0 ]; then
            echo "Setting up single config: $BASE_CONFIG"
            make "${MAKE_FLAGS[@]}" "$BASE_CONFIG"
        else
            echo "Merging configs: $BASE_CONFIG + ${EXTRA_CONFIGS[*]}"
            env "${MAKE_FLAGS[@]}" ./scripts/kconfig/merge_config.sh -O "$OUT_DIR" "arch/arm64/configs/$BASE_CONFIG" "${EXTRA_CONFIGS[@]}"
        fi
        ;;

    kernel)
        if [ ! -f "$OUT_DIR/.config" ]; then
            make "${MAKE_FLAGS[@]}" "$DEFCONFIG"
        fi

        echo "Build started using $THREADS threads"
        START=$(date +%s)

        if make "${MAKE_FLAGS[@]}" -j"$THREADS" Image.gz 2>&1 | tee "$LOG_FILE"; then
            DIFF=$(( $(date +%s) - START ))
            echo "Done! Took $((DIFF / 60))m $((DIFF % 60))s"
        else
            echo "Build failed, check $LOG_FILE"
            exit 1
        fi
        ;;

    *)
        usage
        ;;
esac
