#!/usr/bin/env python3
"""Regression checks for pixelstudio/lpc fixes. Run: python3 -B test_pixelstudio.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image  # noqa: E402

import lpc  # noqa: E402
from pixelstudio import Sprite, strip_checker  # noqa: E402


def test_quantize_ignores_transparent_background():
    s = Sprite(8, 8)
    s.rect(2, 2, 5, 5, "#ff0000")
    s.rect(2, 2, 3, 3, "#00ff00")
    s.quantize(2, dither=False)
    assert set(s.used_colors()) == {(255, 0, 0), (0, 255, 0)}, s.used_colors()


def test_dedupe_merges_into_most_used_and_never_into_merged_colour():
    s = Sprite(8, 1)
    s.px(0, 0, (100, 0, 0))
    for x in range(1, 6):
        s.px(x, 0, (108, 0, 0))
    s.px(6, 0, (118, 0, 0))
    s.dedupe_colors(tol=12)
    assert set(s.used_colors()) == {(108, 0, 0)}, s.used_colors()


def test_strip_checker_keeps_light_pixels_inside_art():
    im = Image.new("RGBA", (5, 5), (230, 230, 230, 255))  # checker bg
    for x in range(1, 4):
        for y in range(1, 4):
            im.putpixel((x, y), (0, 0, 255, 255))
    im.putpixel((2, 2), (255, 255, 255, 255))  # white highlight, enclosed
    out = strip_checker(im)
    assert out.getpixel((0, 0))[3] == 0
    assert out.getpixel((2, 2)) == (255, 255, 255, 255)


def test_lpc_body_does_not_shift_when_a_spear_sticks_out():
    a, b = Image.new("RGBA", (32, 32)), Image.new("RGBA", (32, 32))
    for y in range(10, 30):
        for x in range(12, 20):
            a.putpixel((x, y), (9, 9, 9, 255))
            b.putpixel((x, y), (9, 9, 9, 255))
    for x in range(20, 30):
        b.putpixel((x, 15), (200, 200, 200, 255))
    sh = lpc.LPCSheet().place("thrust", "down", 0, a).place("thrust", "down", 1, b)
    assert sh.cell("thrust", "down", 0).getbbox()[0] == sh.cell("thrust", "down", 1).getbbox()[0]
    big = Image.new("RGBA", (96, 96))  # art at the canvas edge is nudged into the cell
    big.putpixel((0, 50), (1, 1, 1, 255))
    assert lpc.LPCSheet().place("walk", "down", 0, big).cell("walk", "down", 0).getbbox()[0] == 0


def test_frame_indices_checked_and_tags_follow():
    s = Sprite(2, 2)
    s.add_frame()
    s.add_frame()
    for bad in (0, 4):
        try:
            s.del_frame(bad)
            raise AssertionError("del_frame(%d) accepted" % bad)
        except IndexError:
            pass
    s.tag("walk", 1, 3).tag("end", 3, 3)
    s.frame(3)
    s.del_frame(2)
    assert s.tags["walk"]["to"] == 2 and "end" in s.tags and s.tags["end"]["from"] == 2
    assert s.current_frame == 2  # still the frame that was selected
    s.del_frame(2)
    assert "end" not in s.tags and s.tags["walk"] == {"from": 1, "to": 1, "direction": "forward"}
    s.add_frame(after=0)
    assert s.tags["walk"]["from"] == 2
    with tempfile.TemporaryDirectory() as t:
        s.save_gif(os.path.join(t, "x.gif"), tag="walk")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
