# ruff: noqa: SLF001, PLR0915
"""
Provide a thin wrapper around libpyeq36.

The shared library is located with `eq36.paths.get_libpath` and loaded when
this module is imported. The Fortran subroutines are called through `ctypes`
using their gfortran-mangled module symbol names.

@todo Loading the library at import time means that importing `eq36.libpyeq36`
      (or `eq36.data1`) raises `RuntimeError` if the library is missing.
      Consider loading it lazily.
"""

from ctypes import CDLL, POINTER, byref, c_bool, c_char_p, c_double, c_int, c_size_t, create_string_buffer
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from eq36.paths import get_libpath
from eq36.typing import Array1D, Array2D

## The loaded `libpyeq36` shared library
_libeq36 = CDLL(str(get_libpath("pyeq36")))

## The `openin` subroutine, which opens a data1 file and returns its logical unit
_open_data1 = _libeq36.__pyeq36_data1_MOD_openin
_open_data1.argtypes = [c_char_p, POINTER(c_int), POINTER(c_int), c_size_t]
_open_data1.restype = None

## The `closein` subroutine, which closes a logical unit
_close_data1 = _libeq36.__pyeq36_data1_MOD_closein
_close_data1.argtypes = [POINTER(c_int)]
_close_data1.restype = None

## The `indath` subroutine, which reads the header (array allocation sizes) of a data1 file
_read_header = _libeq36.__pyeq36_data1_MOD_indath
_read_header.argtypes = [
    POINTER(c_int),  # data1,
    POINTER(c_int),  # ikta_asv,
    POINTER(c_int),  # ipbt_asv,
    POINTER(c_int),  # ipch_asv,
    POINTER(c_int),  # ipcv_asv,
    POINTER(c_int),  # jpfc_asv,
    POINTER(c_int),  # napa_asv,
    POINTER(c_int),  # narx_asv,
    POINTER(c_int),  # nata_asv,
    POINTER(c_int),  # nbta_asv,
    POINTER(c_int),  # ncta_asv,
    POINTER(c_int),  # ngta_asv,
    POINTER(c_int),  # nlta_asv,
    POINTER(c_int),  # nmta_asv,
    POINTER(c_int),  # npta_asv,
    POINTER(c_int),  # nmuta_asv,
    POINTER(c_int),  # nslta_asv,
    POINTER(c_int),  # nsta_asv,
    POINTER(c_int),  # ntid_asv,
    POINTER(c_int),  # ntpr_asv,
    POINTER(c_int),  # nxta_asv,
    c_char_p,  # udakey,
    POINTER(c_int),  # errno,
]
_read_header.restype = None

## The `indata` subroutine, which reads the body of a data1 file
_read_body = _libeq36.__pyeq36_data1_MOD_indata
_read_body.argtypes = [
    POINTER(c_int),  # byref(data1),
    POINTER(c_double),  # aadh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # aadhh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # aadhv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # aaphi.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdhh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdhv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdot.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdoth.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # abdotv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adadhh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adadhv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adbdhh.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adbdhv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adbdth.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adbdtv.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adhfe.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # adhfsa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # advfe.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # advfsa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # amua.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # aprehw.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # apresg.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # apxa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # aslma.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # atwta.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axhfe.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axhfsa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axlke.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axlksa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axvfe.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # axvfsa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # azeroa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # bpxa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # cco2.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # cdrsa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # cessa.ctypes.data_as(POINTER(c_double))
    POINTER(c_int),  # byref(iapxa_asv)
    POINTER(c_int),  # iapxta.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(iaqsla)
    POINTER(c_int),  # byref(ibpxa_asv)
    POINTER(c_int),  # ibpxta.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(ielam)
    POINTER(c_int),  # byref(igas)
    POINTER(c_int),  # byref(ikta_asv)
    POINTER(c_int),  # insgfa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(ipbt_asv)
    POINTER(c_int),  # byref(ipch)
    POINTER(c_int),  # byref(ipch_asv)
    POINTER(c_int),  # byref(ipcv)
    POINTER(c_int),  # byref(ipcv_asv)
    POINTER(c_int),  # byref(ixrn1a)
    POINTER(c_int),  # byref(ixrn2a)
    POINTER(c_int),  # byref(jpdblo)
    POINTER(c_int),  # byref(jpfc_asv)
    POINTER(c_int),  # byref(jptffl)
    POINTER(c_int),  # jsola.ctypes.data_as(POINTER(c_int))
    POINTER(c_double),  # mwtspa.ctypes.data_as(POINTER(c_double))
    POINTER(c_int),  # nalpaa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(napa_asv)
    POINTER(c_int),  # byref(napta)
    POINTER(c_int),  # byref(narn1a)
    POINTER(c_int),  # byref(narn2a)
    POINTER(c_int),  # byref(narx_asv)
    POINTER(c_int),  # narxt.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(nata)
    POINTER(c_int),  # byref(nata_asv)
    POINTER(c_int),  # nbaspa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(nbta)
    POINTER(c_int),  # byref(nbta_asv)
    POINTER(c_int),  # byref(nbtafd)
    POINTER(c_int),  # byref(nbta1_asv)
    POINTER(c_int),  # ncmpra.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(ncta)
    POINTER(c_int),  # byref(ncta_asv)
    POINTER(c_int),  # ndrsa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(ndrsa_asv)
    POINTER(c_int),  # ndrsra.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # nessa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(nessa_asv)
    POINTER(c_int),  # nessra.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(ngrn1a)
    POINTER(c_int),  # byref(ngrn2a)
    POINTER(c_int),  # byref(ngta)
    POINTER(c_int),  # byref(nlrn1a)
    POINTER(c_int),  # byref(nlrn2a)
    POINTER(c_int),  # byref(nlta)
    POINTER(c_int),  # byref(nmrn1a)
    POINTER(c_int),  # byref(nmrn2a)
    POINTER(c_int),  # byref(nmta)
    POINTER(c_int),  # byref(nmuta)
    POINTER(c_int),  # byref(nmuta_asv)
    POINTER(c_int),  # nmuxa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(npta)
    POINTER(c_int),  # byref(npta_asv)
    POINTER(c_int),  # byref(nslta)
    POINTER(c_int),  # byref(nslta_asv)
    POINTER(c_int),  # nslxa.ctypes.data_as(POINTER(c_int))
    POINTER(c_int),  # byref(nsta)
    POINTER(c_int),  # byref(nsta_asv)
    POINTER(c_int),  # byref(ntid_asv)
    POINTER(c_int),  # byref(ntitld)
    POINTER(c_int),  # byref(ntpr_asv)
    POINTER(c_int),  # byref(ntprt)
    POINTER(c_int),  # byref(nxrn1a)
    POINTER(c_int),  # byref(nxrn2a)
    POINTER(c_int),  # byref(nxta)
    POINTER(c_int),  # byref(nxta_asv)
    POINTER(c_bool),  # qclnsa.ctypes.data_as(POINTER(c_bool))
    POINTER(c_double),  # palpaa.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # byref(tdamax)
    POINTER(c_double),  # byref(tdamin)
    POINTER(c_double),  # tempcu.ctypes.data_as(POINTER(c_double))
    POINTER(c_char_p),  # ubasp.ctypes.data_as(POINTER(c_char_p))
    c_char_p,  # udakey
    c_char_p,  # udatfi
    POINTER(c_char_p),  # uelema.ctypes.data_as(POINTER(c_char_p))
    POINTER(c_char_p),  # uspeca.ctypes.data_as(POINTER(c_char_p))
    POINTER(c_char_p),  # uphasa.ctypes.data_as(POINTER(c_char_p))
    POINTER(c_char_p),  # uptypa.ctypes.data_as(POINTER(c_char_p))
    POINTER(c_char_p),  # utitld.ctypes.data_as(POINTER(c_char_p))
    POINTER(c_double),  # vosp0a.ctypes.data_as(POINTER(c_double))
    POINTER(c_double),  # zchara.ctypes.data_as(POINTER(c_double))
    POINTER(c_int),  # byref(errno)
]
_read_body.restype = None


@dataclass
class Data:
    """
    Provide a loosely structured datatype representing the contents of a data1 file.

    This holds a subset of the arrays read by `indata`, largely unprocessed.
    Arrays are sized by the allocation sizes read from the header rather than
    by the number of entries actually read, so they may have trailing
    zero/blank entries. Index fields are 1-based, as in Fortran.

    @todo The field names mix descriptive names with the original Fortran
          names (`cdrsa`, `nessra`, `narn1a`, ...). Consider settling on one
          convention.
    """

    ## The nominal minimum temperature (Celsius) of the data file (`tdamin`)
    min_temperature: np.float64
    ## The maximum temperature (Celsius) of each temperature range (`tempcu`)
    max_temperature_range: Array1D[np.float64]
    ## The polynomial coefficients for the standard grid pressure (bars) as a
    ## function of temperature, one column per temperature range (`apresg`)
    pressure_coefficients: Array2D[np.float64]
    ## The chemical element names as 8-byte strings (`uelema`)
    element_names: Array1D[np.bytes_]
    ## The atomic weights of the elements (`atwta`)
    atomic_weights: Array1D[np.float64]
    ## The species names as 48-byte strings; the first 24 bytes are the species
    ## name and the last 24 are the name of its phase (`uspeca`)
    species_names: Array1D[np.bytes_]
    ## The molecular weights of the species (`mwtspa`)
    species_molar_weights: Array1D[np.float64]
    ## The flattened reaction coefficients of all species (`cdrsa`)
    cdrsa: Array1D[np.float64]
    ## The electrical charges of the species (`zchara`)
    charges: Array1D[np.float64]
    ## The molar volumes of the species (`vosp0a`)
    volumes: Array1D[np.float64]
    ## The 1-based start and end indices into `nessa` and `cessa` for each
    ## species' elemental composition (`nessra`)
    nessra: Array2D[np.int32]
    ## The 1-based element indices of the species' compositions (`nessa`)
    nessa: Array1D[np.int32]
    ## The element counts of the species' compositions (`cessa`)
    cessa: Array1D[np.float64]
    ## The 1-based index of the first aqueous species
    narn1a: np.int32
    ## The 1-based index of the last aqueous species
    narn2a: np.int32
    ## The 1-based index of the first pure mineral
    nmrn1a: np.int32
    ## The 1-based index of the last pure mineral
    nmrn2a: np.int32
    ## The 1-based index of the first pure liquid
    nlrn1a: np.int32
    ## The 1-based index of the last pure liquid
    nlrn2a: np.int32
    ## The 1-based index of the first gas species
    ngrn1a: np.int32
    ## The 1-based index of the last gas species
    ngrn2a: np.int32
    ## The 1-based index of the first solid-solution end member
    nxrn1a: np.int32
    ## The 1-based index of the last solid-solution end member
    nxrn2a: np.int32


def read_data1(filename: str | Path) -> Data:
    """
    Read a data1 file.

    The file is opened with `openin`, its header is read with `indath` to
    determine the array allocation sizes, the arrays are allocated
    (Fortran-ordered) and the body is read with `indata`. Once the file has
    been opened, it is closed after reading, whether or not an error occurred.
    Most of the data read is discarded; only the subset described by `Data` is
    returned.

    @param filename The path to the data1 file

    @return The parsed data

    @throws RuntimeError if the call to open the file raises an exception or
            reports a non-zero error code (e.g. the file does not exist)
    @throws RuntimeError if the call to read the header raises an exception or
            reports a non-zero error code
    @throws RuntimeError if the call to read the body raises an exception or
            reports a non-zero error code

    @todo This function is long enough to need `noqa: PLR0915`; consider
          splitting allocation and the `indata` call into helpers.
    """
    fname = bytes(str(filename), "ascii")
    data1 = c_int(0)
    errno = c_int(0)

    try:
        _open_data1(fname, byref(data1), byref(errno), len(fname))
    except Exception as e:
        msg = "failed to open data1 file"
        raise RuntimeError(msg) from e

    if errno.value != 0:
        msg = "failed to open data1 file"
        raise RuntimeError(msg)

    try:
        ikta_asv = c_int(-1)
        ipbt_asv = c_int(-1)
        ipch_asv = c_int(-1)
        ipcv_asv = c_int(-1)
        jpfc_asv = c_int(-1)
        napa_asv = c_int(-1)
        narx_asv = c_int(-1)
        nata_asv = c_int(-1)
        nbta_asv = c_int(-1)
        ncta_asv = c_int(-1)
        ngta_asv = c_int(-1)
        nlta_asv = c_int(-1)
        nmta_asv = c_int(-1)
        npta_asv = c_int(-1)
        nmuta_asv = c_int(-1)
        nslta_asv = c_int(-1)
        nsta_asv = c_int(-1)
        ntid_asv = c_int(-1)
        ntpr_asv = c_int(-1)
        nxta_asv = c_int(-1)
        udakey = create_string_buffer(8)

        tdamin = c_double(0.0)
        tdamax = c_double(0.0)
        nxta = c_int(-1)
        nxrn2a = c_int(-1)
        nxrn1a = c_int(-1)
        ntprt = c_int(-1)
        ntitld = c_int(-1)
        nsta = c_int(-1)
        nslta = c_int(-1)
        npta = c_int(-1)
        nmuta = c_int(-1)
        nmta = c_int(-1)
        nmrn1a = c_int(-1)
        nmrn2a = c_int(-1)
        nlta = c_int(-1)
        nlrn1a = c_int(-1)
        nlrn2a = c_int(-1)
        ngta = c_int(-1)
        ngrn1a = c_int(-1)
        ngrn2a = c_int(-1)
        ncta = c_int(-1)
        nbta = c_int(-1)
        nata = c_int(-1)
        narn1a = c_int(-1)
        narn2a = c_int(-1)
        napta = c_int(-1)
        jpdblo = c_int(-1)
        jptffl = c_int(-1)
        ixrn2a = c_int(-1)
        ixrn1a = c_int(-1)
        ipcv = c_int(-1)
        ipch = c_int(-1)
        igas = c_int(-1)
        ielam = c_int(-1)
        iaqsla = c_int(-1)
        udatfi = create_string_buffer(8)

        try:
            _read_header(
                data1,
                byref(ikta_asv),
                byref(ipbt_asv),
                byref(ipch_asv),
                byref(ipcv_asv),
                byref(jpfc_asv),
                byref(napa_asv),
                byref(narx_asv),
                byref(nata_asv),
                byref(nbta_asv),
                byref(ncta_asv),
                byref(ngta_asv),
                byref(nlta_asv),
                byref(nmta_asv),
                byref(npta_asv),
                byref(nmuta_asv),
                byref(nslta_asv),
                byref(nsta_asv),
                byref(ntid_asv),
                byref(ntpr_asv),
                byref(nxta_asv),
                udakey,
                byref(errno),
            )
        except Exception as e:
            msg = "failed to read data1 header"
            raise RuntimeError(msg) from e

        if errno.value != 0:
            msg = "failed to read data1 header"
            raise RuntimeError(msg)

        # These are hardcoded values taken from EQ3/6
        iapxa_asv = c_int(30)
        ibpxa_asv = c_int(10)

        nbtafd = c_int(nbta_asv.value)

        npta_asv = c_int(npta_asv.value)
        nsta_asv = c_int(nsta_asv.value)

        nbta1_asv = c_int(nbta_asv.value + 1)
        ndrsa_asv = c_int(7 * nsta_asv.value)
        nessa_asv = c_int(5 * nsta_asv.value)

        iapxta = np.zeros(nxta_asv.value, dtype=np.int32, order="F")
        ibpxta = np.zeros(nxta_asv.value, dtype=np.int32, order="F")
        jsola = np.zeros(nxta_asv.value, dtype=np.int32, order="F")
        narxt = np.zeros(ntpr_asv.value, dtype=np.int32, order="F")
        nbaspa = np.zeros(nbta_asv.value, dtype=np.int32, order="F")
        ndrsa = np.zeros(ndrsa_asv.value, dtype=np.int32, order="F")
        nessa = np.zeros(nessa_asv.value, dtype=np.int32, order="F")
        ncmpra = np.zeros((2, npta_asv.value), dtype=np.int32, order="F")
        ndrsra = np.zeros((2, nsta_asv.value), dtype=np.int32, order="F")
        nessra = np.zeros((2, nsta_asv.value), dtype=np.int32, order="F")
        qclnsa = np.zeros(nsta_asv.value, dtype=c_int, order="F")
        utitld = np.asarray([bytes(80) for _ in range(ntid_asv.value)], order="F")
        uspeca = np.asarray([bytes(48) for _ in range(nsta_asv.value)], order="F")
        uphasa = np.asarray([bytes(24) for _ in range(npta_asv.value)], order="F")
        uptypa = np.asarray([bytes(24) for _ in range(npta_asv.value)], order="F")
        uelema = np.asarray([bytes(8) for _ in range(ncta_asv.value)], order="F")
        ubasp = np.asarray([bytes(48) for _ in range(nbta_asv.value)], order="F")
        tempcu = np.zeros(ntpr_asv.value, dtype=np.float64, order="F")
        aprehw = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        apresg = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        axhfe = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        axlke = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        axvfe = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        aadh = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        aadhh = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        aadhv = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        aaphi = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdh = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdhh = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdhv = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdot = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdoth = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        abdotv = np.zeros((narx_asv.value, ntpr_asv.value), dtype=np.float64, order="F")
        adadhh = np.zeros((narx_asv.value, ntpr_asv.value, ipch_asv.value), dtype=np.float64, order="F")
        adadhv = np.zeros((narx_asv.value, ntpr_asv.value, ipcv_asv.value), dtype=np.float64, order="F")
        adbdhh = np.zeros((narx_asv.value, ntpr_asv.value, ipch_asv.value), dtype=np.float64, order="F")
        adbdhv = np.zeros((narx_asv.value, ntpr_asv.value, ipcv_asv.value), dtype=np.float64, order="F")
        adbdth = np.zeros((narx_asv.value, ntpr_asv.value, ipch_asv.value), dtype=np.float64, order="F")
        adbdtv = np.zeros((narx_asv.value, ntpr_asv.value, ipcv_asv.value), dtype=np.float64, order="F")
        adhfe = np.zeros((narx_asv.value, ntpr_asv.value, ipch_asv.value), dtype=np.float64, order="F")
        advfe = np.zeros((narx_asv.value, ntpr_asv.value, ipcv_asv.value), dtype=np.float64, order="F")
        axhfsa = np.zeros((narx_asv.value, ntpr_asv.value, nsta_asv.value), dtype=np.float64, order="F")
        axlksa = np.zeros(
            (narx_asv.value, ntpr_asv.value, nsta_asv.value),
            dtype=np.float64,
            order="F",
        )
        axvfsa = np.zeros(
            (narx_asv.value, ntpr_asv.value, nsta_asv.value),
            dtype=np.float64,
            order="F",
        )
        adhfsa = np.zeros((narx_asv.value, ntpr_asv.value, ipch_asv.value, nsta_asv.value), dtype=np.float64, order="F")
        advfsa = np.zeros((narx_asv.value, ntpr_asv.value, ipcv_asv.value, nsta_asv.value), dtype=np.float64, order="F")
        atwta = np.zeros(ncta_asv.value, dtype=np.float64, order="F")
        cdrsa = np.zeros(ndrsa_asv.value, dtype=np.float64, order="F")
        cessa = np.zeros(nessa_asv.value, dtype=np.float64, order="F")
        mwtspa = np.zeros(nsta_asv.value, dtype=np.float64, order="F")
        vosp0a = np.zeros(nsta_asv.value, dtype=np.float64, order="F")
        zchara = np.zeros(nsta_asv.value, dtype=np.float64, order="F")
        apxa = np.zeros((iapxa_asv.value, nxta_asv.value), dtype=np.float64, order="F")
        bpxa = np.zeros((ibpxa_asv.value, nxta_asv.value), dtype=np.float64, order="F")
        azeroa = np.zeros(nata_asv.value, dtype=np.float64, order="F")
        insgfa = np.zeros(nata_asv.value, dtype=np.int32, order="F")
        nalpaa = np.zeros(nslta_asv.value, dtype=np.int32, order="F")
        nmuxa = np.zeros((3, nmuta_asv.value), dtype=np.int32, order="F")
        nslxa = np.zeros((2, nslta_asv.value), dtype=np.int32, order="F")
        amua = np.zeros((jpfc_asv.value, nmuta_asv.value), dtype=np.float64, order="F")
        aslma = np.zeros((jpfc_asv.value, ipbt_asv.value + 1, nslta_asv.value), dtype=np.float64, order="F")
        palpaa = np.zeros((ipbt_asv.value, napa_asv.value), dtype=np.float64, order="F")
        cco2 = np.zeros(5, dtype=np.float64, order="F")

        try:
            _read_body(
                byref(data1),
                aadh.ctypes.data_as(POINTER(c_double)),
                aadhh.ctypes.data_as(POINTER(c_double)),
                aadhv.ctypes.data_as(POINTER(c_double)),
                aaphi.ctypes.data_as(POINTER(c_double)),
                abdh.ctypes.data_as(POINTER(c_double)),
                abdhh.ctypes.data_as(POINTER(c_double)),
                abdhv.ctypes.data_as(POINTER(c_double)),
                abdot.ctypes.data_as(POINTER(c_double)),
                abdoth.ctypes.data_as(POINTER(c_double)),
                abdotv.ctypes.data_as(POINTER(c_double)),
                adadhh.ctypes.data_as(POINTER(c_double)),
                adadhv.ctypes.data_as(POINTER(c_double)),
                adbdhh.ctypes.data_as(POINTER(c_double)),
                adbdhv.ctypes.data_as(POINTER(c_double)),
                adbdth.ctypes.data_as(POINTER(c_double)),
                adbdtv.ctypes.data_as(POINTER(c_double)),
                adhfe.ctypes.data_as(POINTER(c_double)),
                adhfsa.ctypes.data_as(POINTER(c_double)),
                advfe.ctypes.data_as(POINTER(c_double)),
                advfsa.ctypes.data_as(POINTER(c_double)),
                amua.ctypes.data_as(POINTER(c_double)),
                aprehw.ctypes.data_as(POINTER(c_double)),
                apresg.ctypes.data_as(POINTER(c_double)),
                apxa.ctypes.data_as(POINTER(c_double)),
                aslma.ctypes.data_as(POINTER(c_double)),
                atwta.ctypes.data_as(POINTER(c_double)),
                axhfe.ctypes.data_as(POINTER(c_double)),
                axhfsa.ctypes.data_as(POINTER(c_double)),
                axlke.ctypes.data_as(POINTER(c_double)),
                axlksa.ctypes.data_as(POINTER(c_double)),
                axvfe.ctypes.data_as(POINTER(c_double)),
                axvfsa.ctypes.data_as(POINTER(c_double)),
                azeroa.ctypes.data_as(POINTER(c_double)),
                bpxa.ctypes.data_as(POINTER(c_double)),
                cco2.ctypes.data_as(POINTER(c_double)),
                cdrsa.ctypes.data_as(POINTER(c_double)),
                cessa.ctypes.data_as(POINTER(c_double)),
                byref(iapxa_asv),
                iapxta.ctypes.data_as(POINTER(c_int)),
                byref(iaqsla),
                byref(ibpxa_asv),
                ibpxta.ctypes.data_as(POINTER(c_int)),
                byref(ielam),
                byref(igas),
                byref(ikta_asv),
                insgfa.ctypes.data_as(POINTER(c_int)),
                byref(ipbt_asv),
                byref(ipch),
                byref(ipch_asv),
                byref(ipcv),
                byref(ipcv_asv),
                byref(ixrn1a),
                byref(ixrn2a),
                byref(jpdblo),
                byref(jpfc_asv),
                byref(jptffl),
                jsola.ctypes.data_as(POINTER(c_int)),
                mwtspa.ctypes.data_as(POINTER(c_double)),
                nalpaa.ctypes.data_as(POINTER(c_int)),
                byref(napa_asv),
                byref(napta),
                byref(narn1a),
                byref(narn2a),
                byref(narx_asv),
                narxt.ctypes.data_as(POINTER(c_int)),
                byref(nata),
                byref(nata_asv),
                nbaspa.ctypes.data_as(POINTER(c_int)),
                byref(nbta),
                byref(nbta_asv),
                byref(nbtafd),
                byref(nbta1_asv),
                ncmpra.ctypes.data_as(POINTER(c_int)),
                byref(ncta),
                byref(ncta_asv),
                ndrsa.ctypes.data_as(POINTER(c_int)),
                byref(ndrsa_asv),
                ndrsra.ctypes.data_as(POINTER(c_int)),
                nessa.ctypes.data_as(POINTER(c_int)),
                byref(nessa_asv),
                nessra.ctypes.data_as(POINTER(c_int)),
                byref(ngrn1a),
                byref(ngrn2a),
                byref(ngta),
                byref(nlrn1a),
                byref(nlrn2a),
                byref(nlta),
                byref(nmrn1a),
                byref(nmrn2a),
                byref(nmta),
                byref(nmuta),
                byref(nmuta_asv),
                nmuxa.ctypes.data_as(POINTER(c_int)),
                byref(npta),
                byref(npta_asv),
                byref(nslta),
                byref(nslta_asv),
                nslxa.ctypes.data_as(POINTER(c_int)),
                byref(nsta),
                byref(nsta_asv),
                byref(ntid_asv),
                byref(ntitld),
                byref(ntpr_asv),
                byref(ntprt),
                byref(nxrn1a),
                byref(nxrn2a),
                byref(nxta),
                byref(nxta_asv),
                qclnsa.ctypes.data_as(POINTER(c_bool)),
                palpaa.ctypes.data_as(POINTER(c_double)),
                byref(tdamax),
                byref(tdamin),
                tempcu.ctypes.data_as(POINTER(c_double)),
                ubasp.ctypes.data_as(POINTER(c_char_p)),
                udakey,
                udatfi,
                uelema.ctypes.data_as(POINTER(c_char_p)),
                uspeca.ctypes.data_as(POINTER(c_char_p)),
                uphasa.ctypes.data_as(POINTER(c_char_p)),
                uptypa.ctypes.data_as(POINTER(c_char_p)),
                utitld.ctypes.data_as(POINTER(c_char_p)),
                vosp0a.ctypes.data_as(POINTER(c_double)),
                zchara.ctypes.data_as(POINTER(c_double)),
                byref(errno),
            )
        except Exception as e:
            msg = "failed to read data1 body"
            raise RuntimeError(msg) from e

        if errno.value != 0:
            msg = "failed to read data1 body"
            raise RuntimeError(msg)
    finally:
        _close_data1(data1)

    return Data(
        min_temperature=np.float64(tdamin.value),
        max_temperature_range=tempcu,
        pressure_coefficients=apresg,
        element_names=uelema,
        atomic_weights=atwta,
        species_names=uspeca,
        species_molar_weights=mwtspa,
        cdrsa=cdrsa,
        charges=zchara,
        volumes=vosp0a,
        nessra=nessra,
        nessa=nessa,
        cessa=cessa,
        narn1a=np.int32(narn1a.value),
        narn2a=np.int32(narn2a.value),
        nmrn1a=np.int32(nmrn1a.value),
        nmrn2a=np.int32(nmrn2a.value),
        nlrn1a=np.int32(nlrn1a.value),
        nlrn2a=np.int32(nlrn2a.value),
        ngrn1a=np.int32(ngrn1a.value),
        ngrn2a=np.int32(ngrn2a.value),
        nxrn1a=np.int32(nxrn1a.value),
        nxrn2a=np.int32(nxrn2a.value),
    )


__all__ = [
    "Data",
    "read_data1",
]
