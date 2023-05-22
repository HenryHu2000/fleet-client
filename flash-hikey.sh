#!/bin/sh

scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/l-loader/prm_ptable.img ./
scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/tools-images-hikey960/hisi-sec_xloader.img ./
scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/l-loader/l-loader.bin ./
scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/trusted-firmware-a/build/hikey960/release/fip.bin ./
scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/tools-images-hikey960/hisi-nvme.img ./
scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-hikey/out/boot-fat.uefi.img ./

fastboot flash ptable prm_ptable.img
fastboot flash xloader hisi-sec_xloader.img
fastboot flash fastboot l-loader.bin
fastboot flash fip fip.bin
fastboot flash nvme hisi-nvme.img
fastboot flash boot boot-fat.uefi.img
