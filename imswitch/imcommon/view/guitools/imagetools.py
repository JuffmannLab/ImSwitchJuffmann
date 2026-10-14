import numpy as np


def bestLevels(arr):
    # Best cmin, cmax algorithm taken from ImageJ routine:
    # http://cmci.embl.de/documents/120206pyip_cooking/
    # python_imagej_cookbook#automatic_brightnesscontrast_button
    pixelCount = arr.size
    limit = pixelCount / 10
    threshold = pixelCount / 5000
    hist, bin_edges = np.histogram(arr, 256)
    i = 0
    found = False
    count = 0
    while True:
        i += 1
        count = hist[i]
        if count > limit:
            count = 0
        found = count > threshold
        if found or i >= 255:
            break
    hmin = i

    i = 256
    while True:
        i -= 1
        count = hist[i]
        if count > limit:
            count = 0
        found = count > threshold
        if found or i < 1:
            break
    hmax = i

    return bin_edges[hmin], bin_edges[hmax]


def minmaxLevels(arr):
    if np.issubdtype(arr.dtype, np.floating) and arr.size > 1:
        # Differential images (e.g. iScat contrast) are centered around 0 and can contain
        # a few extreme pixels, so use symmetric levels that ignore the outliers
        return symmetricLevels(arr)

    # 10 % headroom: noise and slightly brighter frames don't immediately reach the upper
    # limit (shown red with the grayclip colormap, like saturation)
    minlevel = 0
    maxlevel = arr.max() * 1.1 + 2

    return minlevel, maxlevel


def displayRange(arr, minimum, maximum):
    """ Range of the contrast slider for an image shown with the levels (minimum, maximum):
    the full range of the camera for integer images (12 bit if all values fit, so the levels
    can be raised when the image gets brighter), the range of the data for float images
    (e.g. differential images). Always includes the levels. """
    arr = np.asarray(arr)
    if arr.size == 0:
        return minimum, maximum
    if np.issubdtype(arr.dtype, np.integer):
        if arr.dtype.itemsize == 1:
            full = 255
        else:
            full = 4095 if arr.max() <= 4095 else np.iinfo(arr.dtype).max
        return min(minimum, 0), max(maximum, full)
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return minimum, maximum
    return min(minimum, float(finite.min())), max(maximum, float(finite.max()))


def symmetricLevels(arr, percentile=99.5):
    """ Levels (-m, m) covering all values with 10 % headroom, but at most 3x the given
    percentile of the absolute values (so single extreme pixels don't compress the contrast). """
    finite = np.abs(arr[np.isfinite(arr)])
    m = float(min(finite.max(), 3 * np.percentile(finite, percentile))) * 1.1         if finite.size else 0.0
    if m <= 0:
        m = 1e-6
    return -m, m


# Copyright (C) 2017 Federico Barabas
# This file is part of Tormenta.
#
# Tormenta is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Tormenta is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
