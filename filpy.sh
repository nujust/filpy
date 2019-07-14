#!/bin/bash

THIS=$(readlink -f $0)
EXE=${THIS%.*}

python3 $EXE.py $*
