#!/usr/bin/env python3
import argparse
import sys
import os
import random
import numpy as np
import pickle
from PIL import Image

import circpadsim

ap = argparse.ArgumentParser()
ap.add_argument("--ld", required=True,
    help="load dataset from pickle, provide path to pickled file")

ap.add_argument("-s", default="test",
    help="save filename prefix")

# dimensions of the image
ap.add_argument("-x", type=int, default=5000,
    help="image width (x-axis)")
ap.add_argument("-y", type=int, default=1000,
    help="image height (y-axis)")

ap.add_argument("--hide", required=False, default=False,
    action="store_true", help="hide padding cells")
args = vars(ap.parse_args())

# TOMATO colors below
COLOR_BACKGROUND = [0, 0, 0, 0] # transparent PNG (alpha 0)
COLOR_NONPADDING_RECV = [0, 0, 0, 255] # black - most data is nonpadding received
COLOR_NONPADDING_SENT = [255, 255, 255, 255] # white - sent nonpadding data
COLOR_PADDING_RECV = [170, 57, 57, 255] # red - most padding is received padding
COLOR_PADDING_SENT = [45, 136, 45, 255] # green - outgoing padding

def main():
    print(f"attempting to load dataset from pickle file {args['ld']}")
    dataset, _ = pickle.load(open(args["ld"], "rb"))

    image = Image.fromarray(get_img_data(dataset, args["y"], args["x"]))
    image.save(open(f"{args['s']}.png", "wb"))

def get_img_data(dataset, n, width):
    data = np.full((n, width, 4), COLOR_BACKGROUND, dtype=np.uint8)

    for y, k in enumerate(dataset):
        if y >= n:
            break
        x = 0
        for v in dataset[k][0]:
            if x >= width:
                break
            if v == 1:
                data[y][x] =COLOR_NONPADDING_SENT
                x += 1
            elif v == -1:
                data[y][x] = COLOR_NONPADDING_RECV
                x += 1
            elif not args["hide"] and v == 2:
                data[y][x] = COLOR_PADDING_SENT
                x += 1
            elif not args["hide"] and v == -2:
                data[y][x] = COLOR_PADDING_RECV
                x += 1

    return data

if __name__ == "__main__":
    main()