#!/bin/sh
# usage: post.sh in.jpg out.jpg   (same grade as the film)
ffmpeg -y -loglevel error -i "$1" -frames:v 1 -vf "format=gbrp,split[a][b];[b]curves=all='0/0 0.62/0 1/1',gblur=sigma=22[bl];[a][bl]blend=all_mode=screen:all_opacity=0.8,eq=contrast=1.06:saturation=1.10:gamma=1.04,colorbalance=bs=0.035:rs=-0.01:rm=0.035:bm=-0.045:rh=0.03:bh=-0.05,vignette=angle=PI/8.5,noise=alls=4:allf=t,format=yuvj420p" -q:v 2 "$2"
