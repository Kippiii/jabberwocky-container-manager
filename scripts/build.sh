#!/usr/bin/env bash
set -eu

if [ $# -lt 8 ]; then
    echo "FATAL ERROR: Insufficient arguments."
    exit 1
fi

wd=$1
vpassword=$2
vhostname=$3
vhddsize=$4
vinclude=$5
hostarch=$6
guestarch=$7
scriptfullorder=$8

rootfs=$wd/build/temp/rootfs
result=$wd/build/temp/hdd.qcow2
vmlinuz=$wd/build/temp/vmlinuz
initrd=$wd/build/temp/initrd.img
packagedir=$wd/packages
resourcesdir=$wd/resources
scriptdir=$wd/scripts

if  [[ $hostarch != $guestarch ]]; then
    foreign="--foreign"
else
    foreign=""
fi

if [[ $guestarch == "amd64" ]]; then
    networkdevice="ens3"
    kernel_suffix="5.10.0-20-amd64"
elif [[ $guestarch == "arm64" ]]; then
    networkdevice="enp0s1"
    kernel_suffix="5.10.0-20-arm64"
elif [[ $guestarch == "mipsel" ]]; then
    networkdevice="enp0s11"
    kernel_suffix="5.10.0-20-4kc-malta"
# elif [[ $guestarch == "mips64el" ]]; then
#     networkdevice="enp0s11"
#     kernel_suffix="5.10.0-20-5kc-malta"
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
    --include=linux-image-$kernel_suffix,openssh-server,$vinclude \
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


# Copy resources into home
if [[ -n $(ls $resourcesdir) ]]; then
    sudo cp -r $resourcesdir/* $rootfs/root/
fi


# Install provided .deb packages if applicable
if [[ -n $(ls $packagedir/*.deb) ]]; then
    sudo mkdir -p $rootfs/_packages
    sudo cp $packagedir/*.deb $rootfs/_packages

    cat << EOF | sudo tee $rootfs/_packages/_install_packages.sh
#!/bin/bash
apt install /_packages/*.deb -y
EOF

    sudo chroot $rootfs /bin/bash /_packages/_install_packages.sh 2> $wd/build/package_errors.txt || true
    sudo rm -r $rootfs/_packages
fi


# Run User Scripts
if [[ -n $(ls $scriptdir) ]]; then
    cat << EOF | sudo tee $rootfs/_runscript.sh
#!/bin/bash
cd /root
chmod +x /_script
/_script
EOF

    for sname in ${scriptfullorder[@]}; do
        sudo cp $scriptdir/$sname $rootfs/_script
        sudo chroot $rootfs /bin/bash /_runscript.sh $sname || echo $sname > $wd/build/failed_scripts.txt
        sudo rm $rootfs/_script
    done
    sudo rm $rootfs/_runscript.sh
fi


# Retrieve kernel image and initrd image
sudo cp $rootfs/boot/vmlinuz-$kernel_suffix $vmlinuz
sudo cp $rootfs/boot/initrd.img-$kernel_suffix $initrd


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
