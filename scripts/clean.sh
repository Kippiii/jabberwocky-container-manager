#!/usr/bin/env bash

if [ $# -lt 1 ]; then
    echo "FATAL ERROR: Insufficient arguments."
    exit 1
fi

wd=$1
temp=$wd/build/temp

set -eux
rm -rf $temp/*
