#!/usr/bin/env bash
set -eu

if [ $# -lt 10 ]; then
    echo "FATAL ERROR: Insufficient arguments."
    exit 1
fi

rootfs=$1
result=$2
vmlinuz=$3
initrd=$4
vpassword=$5
vhostname=$6
vhddsize=$7
vinclude=$8
hostarch=$9
guestarch=${10}

if  [[ $hostarch != $guestarch ]]; then
    foreign="--foreign"
else
    foreign=""
fi

if [[ $guestarch == "amd64" ]]; then
    networkdevice="ens3"
elif [[ $guestarch == "arm64" ]]; then
    networkdevice="enp0s1"
else
    echo "FATAL ERROR: Unknown architecture: $guestarch"
    exit 1
fi


# Acquire root privileges & set up environment
echo "Temporary superuser privileges are required to continue."
echo "If you wish to review the contents of this script it is available in plain text at $0"
sudo echo

set -eux
# -----------------
# -- Begin Build --
# -----------------


# Initial debootstrap
sudo debootstrap \
    --arch=$guestarch $foreign \
    --include=linux-image-5.10.0-20-$guestarch,openssh-server,$vinclude \
    --components=main,contrib,non-free \
    bullseye \
    $rootfs \
    http://deb.debian.org/debian/;

if [[ $hostarch != $guestarch ]]; then
    sudo chroot $rootfs /debootstrap/debootstrap --second-stage
fi


# Set root password
echo "root:$vpassword" | sudo chroot $rootfs chpasswd

sudo chroot $rootfs mkdir /root/.ssh

# System configuration
cat << EOF | sudo tee $rootfs/etc/fstab
/dev/sda1 / ext2 errors=remount-ro,noatime 0 1
EOF

cat << EOF | sudo tee "$rootfs/etc/network/interfaces"
source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
allow-hotplug $networkdevice
iface $networkdevice inet dhcp
EOF

cat << EOF | sudo tee -a "$rootfs/etc/ssh/sshd_config"

# Added automatically by Jabberwocky
PermitRootLogin yes
AllowUsers *@localhost
AllowUsers *@10.0.2.2
EOF

cat << EOF | sudo tee "$rootfs/etc/hostname"
$vhostname
EOF

# Retrieve kernel image and initrd image
sudo cp $rootfs/boot/vmlinuz-5.10.0-20-$guestarch $vmlinuz
sudo cp $rootfs/boot/initrd.img-5.10.0-20-$guestarch $initrd


# Generate virtual hard disk
echo "Creating filesystem..."
sudo virt-make-fs \
    --format=qcow2 \
    --partition=mbr \
    --size +100M \
    --type ext2 \
    $rootfs \
    $result.tmp;

sudo qemu-img create -f qcow2 $result $vhddsize
sudo virt-resize --expand /dev/sda1 $result.tmp $result

# Clean temporary files
sudo rm -f $result.tmp
sudo rm -rf $rootfs

# Finalize
sudo chown $(whoami) $result $vmlinuz $initrd
sudo chgrp $(whoami) $result $vmlinuz $initrd


# qemu-system-x86_64 -kernel vmlinuz -initrd initrd.img -append 'console=ttyS0 root=/dev/sda1' -serial mon:stdio -nographic -m 1G -drive file=hdd.qcow2,format=qcow2 -net nic -net user,hostfwd=tcp::12350-:22
# qemu-system-aarch64 -M virt -cpu cortex-a53 -nographic -smp 1 -kernel vmlinuz -initrd initrd.img -append "console=ttyAMA0 root=/dev/vda1" -drive file=hdd.qcow2,format=qcow2 -m 1G -net nic -net user,hostfwd=tcp::12350-:22
