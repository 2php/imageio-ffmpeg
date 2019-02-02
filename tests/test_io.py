import os
import types
import tempfile
from urllib.request import urlopen

from pytest import skip

import imageio_ffmpeg


if os.getenv("TRAVIS_OS_NAME") == "windows":
    skip(
        "Skip this on the Travis Windows run for now, see #408", allow_module_level=True
    )


test_dir = tempfile.gettempdir()
test_url = "https://raw.githubusercontent.com/imageio/imageio-binaries/master/images/cockatoo.mp4"
test_file1 = os.path.join(test_dir, "cockatoo.mp4")
test_file2 = os.path.join(test_dir, "test.mp4")


def setup_module():
    bb = urlopen(test_url, timeout=5).read()
    with open(test_file1, "wb") as f:
        f.write(bb)


def test_ffmpeg_version():
    version = imageio_ffmpeg.get_ffmpeg_version()
    assert version > "3.0"


def test_read_nframes():
    nframes, nsecs = imageio_ffmpeg.count_frames_and_secs(test_file1)
    assert nframes == 280
    assert 13.80 < nsecs < 13.99


def test_reading1():

    # Calling returns a generator
    gen = imageio_ffmpeg.read_frames(test_file1)
    assert isinstance(gen, types.GeneratorType)

    # First yield is a meta dict
    meta = gen.__next__()
    assert isinstance(meta, dict)
    for key in ("size", "fps", "duration"):
        assert key in meta

    # Read frames
    framesize = meta["size"][0] * meta["size"][1] * 3
    assert framesize == 1280 * 720 * 3
    count = 0
    for frame in gen:
        assert isinstance(frame, bytes) and len(frame) == framesize
        count += 1

    assert count == 280


def test_reading2():
    # Same as 1, but using other pixel format

    gen = imageio_ffmpeg.read_frames(test_file1, pix_fmt="gray", bpp=1)
    meta = gen.__next__()
    framesize = meta["size"][0] * meta["size"][1] * 1
    assert framesize == 1280 * 720 * 1

    count = 0
    for frame in gen:
        count += 1
        assert isinstance(frame, bytes) and len(frame) == framesize

    assert count == 280


def test_reading3():
    # Same as 1, but using other fps

    gen = imageio_ffmpeg.read_frames(test_file1, output_params=["-r", "5.0"])
    meta = gen.__next__()
    framesize = meta["size"][0] * meta["size"][1] * 3
    assert framesize == 1280 * 720 * 3

    count = 0
    for frame in gen:
        count += 1
        assert isinstance(frame, bytes) and len(frame) == framesize

    assert 50 < count < 100  # because smaller fps, same duration


def test_write1():

    for n in (1, 9, 14, 279, 280, 281):

        # Prepare for writing
        gen = imageio_ffmpeg.write_frames(test_file2, (64, 64))
        assert isinstance(gen, types.GeneratorType)
        gen.send(None)  # seed

        # Write n frames
        for i in range(n):
            data = bytes([min(255, 100 + i * 10)] * 64 * 64 * 3)
            gen.send(data)
        gen.close()

        # Check that number of frames is correct
        nframes, nsecs = imageio_ffmpeg.count_frames_and_secs(test_file2)
        assert nframes == n

        # Check again by actually reading
        gen2 = imageio_ffmpeg.read_frames(test_file2)
        gen2.__next__()  # == meta
        count = 0
        for frame in gen2:
            count += 1
        assert count == n


def test_write_pix_fmt_in():

    sizes = []
    for pixfmt, bpp in [("gray", 1), ("rgb24", 3), ("rgba", 4)]:
        # Prepare for writing
        gen = imageio_ffmpeg.write_frames(test_file2, (64, 64), pix_fmt_in=pixfmt)
        gen.send(None)  # seed
        for i in range(9):
            data = bytes([min(255, 100 + i * 10)] * 64 * 64 * bpp)
            gen.send(data)
        gen.close()
        with open(test_file2, "rb") as f:
            sizes.append(len(f.read()))
        # Check nframes
        nframes, nsecs = imageio_ffmpeg.count_frames_and_secs(test_file2)
        assert nframes == 9


def test_write_pix_fmt_out():

    sizes = []
    for pixfmt in ["gray", "yuv420p"]:
        # Prepare for writing
        gen = imageio_ffmpeg.write_frames(test_file2, (64, 64), pix_fmt_out=pixfmt)
        gen.send(None)  # seed
        for i in range(9):
            data = bytes([min(255, 100 + i * 10)] * 64 * 64 * 3)
            gen.send(data)
        gen.close()
        with open(test_file2, "rb") as f:
            sizes.append(len(f.read()))
        # Check nframes
        nframes, nsecs = imageio_ffmpeg.count_frames_and_secs(test_file2)
        assert nframes == 9

    assert sizes[0] < sizes[1]


def test_write_quality():

    sizes = []
    for quality in [2, 5, 9]:
        # Prepare for writing
        gen = imageio_ffmpeg.write_frames(test_file2, (64, 64), quality=quality)
        gen.send(None)  # seed
        for i in range(9):
            data = bytes([min(255, 100 + i * 10)] * 64 * 64 * 3)
            gen.send(data)
        gen.close()
        with open(test_file2, "rb") as f:
            sizes.append(len(f.read()))
        # Check nframes
        nframes, nsecs = imageio_ffmpeg.count_frames_and_secs(test_file2)
        assert nframes == 9

    assert sizes[0] < sizes[1] < sizes[2]


if __name__ == "__main__":
    setup_module()
    test_ffmpeg_version()
    test_read_nframes()
    test_reading1()
    test_reading2()
    test_write1()
    test_write_pix_fmt_in()
    test_write_pix_fmt_out()
    test_write_quality()