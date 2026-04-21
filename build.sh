#!/bin/sh

### Made by github.com/darkydtm. Do not confuse with the original instrument

#### Usage: build.sh <config/kernel>
#### Clang version: r416183b1
#### Link for Clang: https://android.googlesource.com/platform//prebuilts/clang/host/linux-x86/+archive/b669748458572622ed716407611633c5415da25c/clang-r416183b.tar.gz

### Required packages: build-essential bc bison flex git libssl-dev libelf-dev libncurses-dev python3 python-is-python3 zip unzip lz4 zstd pahole device-tree-compiler ccache

#!/bin/bash

OUT_DIR="out"
DEFCONFIG="vendor/lahaina-qgki_defconfig"
LOG_FILE="build.log"
THREADS=$(nproc --all)

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
)

usage() {
	echo "Usage: $0 <config|kernel>"
	exit 1
}

if [ -z "$1" ]; then
	usage
fi

mkdir -p $OUT_DIR

case "$1" in
	"config")
		echo "Setting up: $DEFCONFIG"
		make "${MAKE_FLAGS[@]}" "$DEFCONFIG"
		;;
		
	"kernel")
		echo "Build started using $THREADS threads"
		START=$(date +%s)

		make "${MAKE_FLAGS[@]}" -j"$THREADS" Image.gz 2>&1 | tee "$LOG_FILE"

		if [ ${PIPESTATUS[0]} -eq 0 ]; then
			END=$(date +%s)
			DIFF=$((END - START))
			echo "Success! Duration: $((DIFF / 60))m $((DIFF % 60))s"
		else
			echo "Build failed! Check $LOG_FILE"
			exit 1
		fi
		;;
		
	*)
		usage
		;;
esac
