"""Build the bundled point-lookup grid from the Sacks et al. unfilled 0.5° archive."""
import argparse
import gzip
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import tarfile

import numpy as np
from scipy.io import netcdf_file

SOURCE_SHA256 = "45e8fcb6564036410a1c6085858430ee4e3479df5c20cb283d14a14b74ecb713"


def build(source: Path, output: Path) -> None:
    if sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Archive differs from the documented source release.")
    names, layers = [], []
    with tarfile.open(source) as archive:
        for member in sorted(archive.getmembers(), key=lambda m: m.name):
            name = member.name.removesuffix(".crop.calendar.nc.gz")
            with netcdf_file(BytesIO(gzip.decompress(archive.extractfile(member).read())), mmap=False) as dataset:
                np.testing.assert_allclose(dataset.variables["latitude"][:], np.arange(89.75, -90, -.5), atol=.00005)
                np.testing.assert_allclose(dataset.variables["longitude"][:], np.arange(-179.75, 180, .5), atol=.00005)
                dates = []
                for key in ("plant", "harvest"):
                    var = dataset.variables[key]
                    assert var.dimensions == ("latitude", "longitude") and var.units == b"day of year"
                    valid = var[:] != var._FillValue
                    half_days = np.where(valid, var[:], 0) * 2
                    assert (half_days == np.rint(half_days)).all() and half_days.max() <= 730
                    dates.append(half_days.astype(np.int16))
                names.append(name)
                layers.append(dates)
    np.savez_compressed(output, crops=names, half_days=np.array(layers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
