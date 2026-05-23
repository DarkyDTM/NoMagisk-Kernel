#!/bin/bash

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
    echo "Usage: $0 <config [base_defconfig] [extra1.config ...] | kernel>"
    exit 1
}

[ -z "$1" ] && usage

mkdir -p $OUT_DIR

case "$1" in
    config)
        shift
        if [ $# -gt 0 ]; then
            BASE_CONFIG="$1"
            shift
            EXTRA_CONFIGS=("$@")
        else
            BASE_CONFIG="$DEFCONFIG"
            EXTRA_CONFIGS=()
        fi

        if [ ! -f "arch/arm64/configs/$BASE_CONFIG" ]; then
            echo "Error: Base config arch/arm64/configs/$BASE_CONFIG not found!"
            exit 1
        fi

        if [ ${#EXTRA_CONFIGS[@]} -eq 0 ]; then
            echo "Setting up single config: $BASE_CONFIG"
            make "${MAKE_FLAGS[@]}" "$BASE_CONFIG"
        else
            echo "Merging configs..."
            echo "Base: $BASE_CONFIG"
            echo "Fragments: ${EXTRA_CONFIGS[*]}"
            
            ARCH=arm64 \
            LLVM=1 \
            LLVM_IAS=1 \
            CC=clang \
            LD=ld.lld \
            AR=llvm-ar \
            NM=llvm-nm \
            OBJCOPY=llvm-objcopy \
            OBJDUMP=llvm-objdump \
            STRIP=llvm-strip \
            CLANG_TRIPLE=aarch64-linux-gnu- \
            ./scripts/kconfig/merge_config.sh -O "$OUT_DIR" "arch/arm64/configs/$BASE_CONFIG" "${EXTRA_CONFIGS[@]}"
        fi
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
