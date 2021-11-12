#!/bin/bash

mkdir -p /opt/gfx-mpc
cp gfxmpc.py /opt/gfx-mpc
cp unifont-14.0.01.pcf /opt/gfx-mpc
cp gfx-mpc.service /lib/systemd/system
systemctl enable gfx-mpc
