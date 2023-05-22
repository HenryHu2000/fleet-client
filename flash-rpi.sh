scp hh2119@maru01.doc.res.ic.ac.uk:/home/hh2119/workspace/optee-rpi/build/../out-br/images/rootfs.cpio.gz ./
sudo wipefs -a /dev/sda1
sudo wipefs -a /dev/sda2
sudo wipefs -a /dev/sda

(
  echo n;
  echo p;
  echo 1;
  echo ;
  echo +64M;
  echo n;
  echo p;
  echo 2;
  echo ;
  echo ;
  echo t;
  echo 1;
  echo e;
  echo a;
  echo 1;
  echo p;
  echo w;
) | sudo fdisk /dev/sda

command='
mkfs.vfat -F16 -n BOOT /dev/sda1
mkdir -p /media/boot
mount /dev/sda1 /media/boot
cd /media
gunzip -cd /home/henry/workspace/rpi-optee/rootfs.cpio.gz | sudo cpio -idmv "boot/*"
umount boot

mkfs.ext4 -L rootfs /dev/sda2
mkdir -p /media/rootfs
mount /dev/sda2 /media/rootfs
cd rootfs
gunzip -cd /home/henry/workspace/rpi-optee/rootfs.cpio.gz | sudo cpio -idmv
rm -rf /media/rootfs/boot/*
cd .. && umount rootfs
'

sudo su -c "$command"
