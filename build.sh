#!/bin/bash

### Made by github.com/darkydtm. Do not confuse with the original instrument
#### Usage: build.sh <config/kernel>

OUT_DIR="out"
DEFCONFIG="nomagisk_defconfig"
LOG_FILE="build.log"
THREADS=$(nproc --all)

RAW_BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse --short HEAD)

case "$RAW_BRANCH" in
    lineage-23.2)      BRANCH="stable" ;;
    lineage-23.2-test) BRANCH="unstable" ;;
    *)                 BRANCH="unknown" ;;
esac

MAKE_FLAGS=(
    O=$OUT_DIR
    ARCH=arm64
    LLVM=1
    LLVM_IAS=1
    CC=clang
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
    echo "Usage: $0 <config|kernel>"
    exit 1
}

[ -z "$1" ] && usage

mkdir -p $OUT_DIR

case "$1" in
    config)
        echo "Setting up: $DEFCONFIG"
        make "${MAKE_FLAGS[@]}" "$DEFCONFIG"
        ;;

    kernel)
        if [ ! -f "$OUT_DIR/.config" ]; then
            echo "Config not found, running defconfig first..."
            make "${MAKE_FLAGS[@]}" "$DEFCONFIG"
        fi

        echo "Build started using $THREADS threads"
        START=$(date +%s)

        make "${MAKE_FLAGS[@]}" -j"$THREADS" Image.gz 2>&1 | tee "$LOG_FILE"

        if [ ${PIPESTATUS[0]} -eq 0 ]; then
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
