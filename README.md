![Banner](banner.png)
# Vanilla Kernel - Magiskless experience

Project to add **VanillaSU** (a KernelSU fork with **SUSFS**) and **useful patches** to **LineageOS** without losing vanilla for OnePlus 9 Pro

## Features

- **Base:** Linux 5.4.302, LineageOS source for OnePlus 9 Pro (`sm8350` / `lahaina`)
- **Root:** [VanillaSU](https://github.com/vanilla-kernel/VanillaSU) - a KernelSU-Next fork, vendored as the `KernelSU` submodule
- **SUSFS:** mount/kstat/uname spoofing and related hiding features enabled
- **Packaging:** flashable AnyKernel3 zip, SmartPack-Kernel Manager update channel

## Warning
Installing kernels older than 2.1.1 causes bootloop in the system and recovery due to upstream updates

## Dependencies

```bash
sudo apt-get install -y \
    build-essential bc bison flex git \
    libssl-dev libelf-dev libncurses-dev \
    python3 python-is-python3 \
    zip unzip lz4 zstd pahole \
    device-tree-compiler ccache
```

## Toolchain

Clang **r416183b** (the same toolchain the CI uses - see `.github/workflows/build.yml`):

```bash
mkdir -p ~/clang
wget "https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86/+archive/b669748458572622ed716407611633c5415da25c/clang-r416183b.tar.gz" \
    -O clang.tar.gz
tar -xf clang.tar.gz -C ~/clang
export PATH="$HOME/clang/bin:$PATH"
```

## Building

Make sure the `KernelSU` submodule is checked out first:

```bash
git submodule update --init --recursive
```

The `build.sh` script in the tools/ directory accepts the following commands:

```bash
# Generate configuration (requires base defconfig, e.g. vendor/lahaina-qgki_defconfig):
tools/build.sh config vendor/lahaina-qgki_defconfig

# Or generate with a config fragment (merge):
tools/build.sh config vendor/lahaina-qgki_defconfig arch/arm64/configs/vanillaKernel-defconfig

# Build kernel:
tools/build.sh kernel
```

The CI builds the kernel on every push to `lineage-23.2` (stable) and
`lineage-23.2-test` (unstable), and uploads the flashable AnyKernel3 zip as a
workflow artifact.

## Installation

Flash the resulting `VanillaKernel-*.zip` from a custom recovery, or via the
SmartPack-Kernel Manager update channel (see `smartpack/update.json`).

## Credits

- [LineageOS](https://github.com/LineageOS/android_kernel_oneplus_sm8350) - base kernel source
- [KernelSU-Next](https://github.com/KernelSU-Next/KernelSU-Next) - upstream root solution
- [VanillaSU](https://github.com/vanilla-kernel/VanillaSU) - KernelSU-Next fork used by this kernel
- [SUSFS](https://gitlab.com/simonpunk/susfs4ksu) - root-hiding filesystem layer
- [AnyKernel3](https://github.com/osm0sis/AnyKernel3) - flashable packaging

## License

Released under the terms of the GNU General Public License v2. See `COPYING`.
