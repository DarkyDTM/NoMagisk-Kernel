# AnyKernel3 for OnePlus 9 Pro (lemonadep) - lahaina
properties() { '
kernel.string=Vanilla kernel for OnePlus 9 Pro
do.devicecheck=1
do.modules=0
do.systemless=1
do.cleanup=1
do.cleanuponabort=0
device.name1=lemonadep
device.name2=OnePlus9Pro
device.name3=
supported.versions=
supported.patchlevels=
supported.vendorpatchlevels=
'; }

BLOCK=boot;
IS_SLOT_DEVICE=1;
RAMDISK_COMPRESSION=auto;
PATCH_VBMETA_FLAG=auto;

. tools/ak3-core.sh;

split_boot;
flash_boot;
