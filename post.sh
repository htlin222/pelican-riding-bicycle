#!/bin/sh
# usage: post.sh in.jpg out.jpg   (same grade as the film)
ffmpeg -y -loglevel error -i "$1" -vf "format=gbrp,split[a][b];[b]curves=all='0/0 0.72/0 1/1',gblur=sigma=16[bl];[a][bl]blend=all_mode=screen:all_opacity=0.6,eq=contrast=1.04:saturation=1.12:gamma=1.06,colorbalance=bs=0.04:rs=-0.015:rh=0.03:bh=-0.04,vignette=angle=PI/7,noise=alls=4:allf=t,format=yuvj420p" -q:v 2 "$2"
