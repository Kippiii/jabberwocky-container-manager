#!/usr/bin/env bash
set -eu

if [ $# -lt 9 ]; then
    echo "FATAL ERROR: Insufficient arguments."
    exit 1
fi

username=$1
usergroup=$2
wd=$3
vpassword=$4
vhostname=$5
vhddsize=$6
aptpkgs=$7
hostarch=$8
guestarch=$9
scriptfullorder=${10}
release=${11}

rootfs=$wd/build/temp/rootfs
result=$wd/build/temp/hdd.qcow2
vmlinuz=$wd/build/temp/vmlinuz
initrd=$wd/build/temp/initrd.img
packagedir=$wd/packages
resourcesdir=$wd/resources
scriptdir=$wd/scripts

[[ $hostarch != $guestarch ]] && foreign="--foreign" || foreign=""

if [[ $release == "bullseye" ]]; then
    kernel_version="5.10.0-20"
elif [[ $release == "bookworm" ]]; then
    kernel_version="6.1.0-7"
else
    echo "FATAL ERROR: Unknown release: $release"
    exit 1
fi

if [[ $guestarch == "amd64" ]]; then
    networkdevice="ens3"
    kernel_suffix="amd64"
elif [[ $guestarch == "arm64" ]]; then
    networkdevice="enp0s1"
    kernel_suffix="arm64"
elif [[ $guestarch == "mipsel" ]]; then
    networkdevice="enp0s11"
    kernel_suffix="4kc-malta"
# elif [[ $guestarch == "mips64el" ]]; then
#     networkdevice="enp0s11"
#     kernel_suffix="5.10.0-20-5kc-malta"
else
    echo "FATAL ERROR: Unknown architecture: $guestarch"
    exit 1
fi


set -eux
# -----------------
# -- Begin Build --
# -----------------


# Initial debootstrap
debootstrap \
    --arch=$guestarch $foreign \
    --include=linux-image-$kernel_version-$kernel_suffix,openssh-server \
    --components=main,contrib,non-free \
    $release \
    $rootfs \
    http://deb.debian.org/debian/;

if [[ $hostarch != $guestarch ]]; then
    chroot $rootfs /debootstrap/debootstrap --second-stage
fi

# Retrieve kernel image and initrd image
cp $rootfs/boot/vmlinuz-$kernel_version-$kernel_suffix $vmlinuz
cp $rootfs/boot/initrd.img-$kernel_version-$kernel_suffix $initrd
chown $username $vmlinuz $initrd
chgrp $usergroup $vmlinuz $initrd
chroot $rootfs apt purge --autoremove -y linux-image-$kernel_version-$kernel_suffix

chroot $rootfs mkdir -p /root/.ssh

# System configuration
cat << EOF | tee $rootfs/etc/fstab
/dev/sda1 / ext2 errors=remount-ro,noatime 0 1
EOF

cat << EOF | tee "$rootfs/etc/network/interfaces"
source /etc/network/interfaces.d/*

# The loopback network interface
auto lo
iface lo inet loopback

# The primary network interface
allow-hotplug $networkdevice
iface $networkdevice inet dhcp
EOF

cat << EOF | tee -a "$rootfs/etc/ssh/sshd_config"

# Added automatically by Jabberwocky
PermitRootLogin yes
AllowUsers *@localhost
AllowUsers *@10.0.2.2
EOF

cat << EOF | tee "$rootfs/etc/hostname"
$vhostname
EOF

# Install aptpkgs
if [[ -n $aptpkgs ]]; then
    chroot $rootfs apt -y install $aptpkgs
fi

# Copy resources into home
if [[ -n $(ls $resourcesdir) ]]; then
    cp -r $resourcesdir/* $rootfs/root/
fi

# Install provided .deb packages if applicable
if [[ -n $(ls $packagedir/*.deb) ]]; then
    mkdir -p $rootfs/_packages
    cp $packagedir/*.deb $rootfs/_packages

    cat << EOF | tee $rootfs/_packages/_install_packages.sh
#!/bin/bash
apt install /_packages/*.deb -y
EOF

    chroot $rootfs /bin/bash /_packages/_install_packages.sh 2> $wd/build/package_errors.txt || true
    rm -r $rootfs/_packages
fi

# Run User Scripts
if [[ -n $(ls $scriptdir) ]]; then
    cat << EOF | tee $rootfs/_runscript.sh
#!/bin/bash
cd /root
chmod +x /_script
/_script
EOF

    for sname in ${scriptfullorder[@]}; do
        cp $scriptdir/$sname $rootfs/_script
        chroot $rootfs /bin/bash /_runscript.sh || echo $sname > $wd/build/failed_scripts.txt
        rm $rootfs/_script
    done
    rm $rootfs/_runscript.sh
fi

# Set root password
echo "root:$vpassword" | chroot $rootfs chpasswd

# Generate virtual hard disk
du_output=$(du -sh $rootfs | awk '{print $1}')
unit=$(echo "$du_output" | sed 's/[0-9.]//g')
size=$(echo "$du_output" | sed 's/[A-Za-z]//g')
size=$(printf "%0.f" "$size")

if [[ -r /boot/vmlinuz-$(uname -r) ]]; then
    chown -R $username $rootfs
    chgrp -R $usergroup $rootfs

    sudo -u $username virt-make-fs \
            --format=qcow2 \
            --partition=mbr \
            --size +$size$unit \
            --type ext2 \
            $rootfs \
            $result.tmp;
    rm -rf $rootfs

    sudo -u $username qemu-img create -f qcow2 $result $vhddsize
    sudo -u $username virt-resize --expand /dev/sda1 $result.tmp $result

    rm -f $result.tmp
else
    virt-make-fs \
        --format=qcow2 \
        --partition=mbr \
        --size +$size$unit \
        --type ext2 \
        $rootfs \
        $result.tmp;
    rm -rf $rootfs

    qemu-img create -f qcow2 $result $vhddsize
    virt-resize --expand /dev/sda1 $result.tmp $result

    # Clean temporary files
    rm -f $result.tmp

    # Finalize
    chown $username $result
    chgrp $usergroup $result
fi
