!> Read EQ3/6 data1 files so that their contents can be accessed from Python.
!!
!! The routines here are adapted from the EQLIB routines of EQ3/6 which read the binary data1 files
!! produced by EQPT. The public routines are called from Python, via `ctypes`, by `eq36.libpyeq36`.
!! A data1 file is read by calling, in order:
!!
!! - `openin`, to open the file;
!! - `indath`, to read the header, which gives the array allocation sizes (`*_asv`) required by
!!   `indata`;
!! - `indata`, to read the rest of the file into arrays allocated by the caller;
!! - `closein`, to close the file.
!!
!! Arrays are dimensioned by the allocation sizes, and indices are 1-based. Species are indexed in
!! the order in which they are read: aqueous species, pure minerals, pure liquids (water, cloned
!! from the aqueous species), gas species, and finally solid-solution end members (cloned from the
!! pure minerals).
!!
!! Errors are not reported individually. The messages written by the original EQLIB routines have
!! been removed, and errors are only counted, in `errno` or `nerr`.
module pyeq36_data1
    implicit none

    private

    public :: openin
    public :: closein
    public :: indath
    public :: indata

contains

    !> Open a data1 file for unformatted reading.
    !!
    !! The file is opened on a new logical unit (with `newunit`).
    !!
    !! @param[in]  filename     The path to the file
    !! @param[out] logical_unit The logical unit on which the file is opened
    !! @param[out] errno        404 if the file does not exist, 403 if it could not be opened, and
    !!                          unchanged otherwise
    subroutine openin(filename, logical_unit, errno)
        character(*), intent(in) :: filename
        integer, intent(out) :: logical_unit, errno

        logical exists

        errno = 0

        inquire(file=filename, exist=exists)
        if (.not. exists) then
            errno = 404
            go to 999
        end if

        open(file=filename, form='unformatted', newunit=logical_unit, err=10)
        go to 999

        10 errno = 403

        999 continue
    end subroutine openin

    !> Close a logical unit.
    !!
    !! @param[in] logical_unit The logical unit to close
    subroutine closein(logical_unit)
        integer, intent(inout) :: logical_unit
        close(logical_unit)
    end subroutine closein

    !> Read the header of a data1 file.
    !!
    !! The file is rewound and read from its start. The header consists of a record containing the
    !! string `data1` (to ensure that the file is indeed a data1 file), a record containing the
    !! keystring for the activity coefficient model for aqueous species to which the data file
    !! corresponds (`SEDH` or `Pitzer`), and the array allocation sizes required to store the rest
    !! of the data on the file. On return, the file is positioned for `indata`.
    !!
    !! The Pitzer allocation sizes (`napa_asv`, `nslta_asv`, `nmuta_asv` and `jpfc_asv`) are read
    !! only for `Pitzer` data files, and are otherwise set to 1. `ipbt_asv` is not read, but set to
    !! 2 for `Pitzer` data files and 1 otherwise.
    !!
    !! @param[in]  data1     The logical unit of the open data1 file
    !! @param[out] ikta_asv  The maximum number of end-member component species in any solid
    !!                       solution
    !! @param[out] ipbt_asv  The maximum number of Pitzer alpha parameters for any species pair
    !! @param[out] ipch_asv  The maximum order of the pressure corrections to enthalpy functions
    !! @param[out] ipcv_asv  The maximum order of the pressure corrections to volume functions; the
    !!                       maximum order of the pressure corrections to log K and other
    !!                       Gibbs-energy-based functions is one greater
    !! @param[out] jpfc_asv  The number of coefficients in the Pitzer parameter temperature function
    !! @param[out] napa_asv  The number of distinct sets of Pitzer alpha parameters
    !! @param[out] narx_asv  The maximum number of coefficients per temperature range
    !! @param[out] nata_asv  The number of aqueous species
    !! @param[out] nbta_asv  The number of basis species
    !! @param[out] ncta_asv  The number of chemical elements
    !! @param[out] ngta_asv  The number of gas species
    !! @param[out] nlta_asv  The number of pure liquids
    !! @param[out] nmta_asv  The number of pure minerals
    !! @param[out] npta_asv  The number of phases of all types
    !! @param[out] nmuta_asv The number of ion triplets for which Pitzer mu coefficients are defined
    !! @param[out] nslta_asv The number of ion pairs for which Pitzer S-lambda coefficients are
    !!                       defined
    !! @param[out] nsta_asv  The number of species of all types
    !! @param[out] ntid_asv  The number of lines in the data file title
    !! @param[out] ntpr_asv  The number of temperature ranges
    !! @param[out] nxta_asv  The number of solid-solution phases
    !! @param[out] udakey    The activity coefficient model keystring, e.g. `SEDH` or `Pitzer`
    !! @param[out] errno     420 if the file is not a data1 file, and unchanged otherwise
    !!
    !! @note These are allocation sizes, i.e. upper bounds, which need not equal the numbers of
    !!       entities that `indata` reads.
    subroutine indath(data1, ikta_asv, ipbt_asv, ipch_asv, ipcv_asv, jpfc_asv, &
                      napa_asv, narx_asv, nata_asv, nbta_asv, ncta_asv, ngta_asv, &
                      nlta_asv, nmta_asv, npta_asv, nmuta_asv, nslta_asv, &
                      nsta_asv, ntid_asv, ntpr_asv, nxta_asv, udakey, errno)

        integer, intent(in) :: data1

        integer, intent(out) :: ikta_asv
        integer, intent(out) :: ipbt_asv
        integer, intent(out) :: napa_asv
        integer, intent(out) :: nata_asv
        integer, intent(out) :: nbta_asv
        integer, intent(out) :: ncta_asv
        integer, intent(out) :: ngta_asv
        integer, intent(out) :: nlta_asv
        integer, intent(out) :: nmta_asv
        integer, intent(out) :: npta_asv
        integer, intent(out) :: nmuta_asv
        integer, intent(out) :: nslta_asv
        integer, intent(out) :: nsta_asv
        integer, intent(out) :: ntid_asv
        integer, intent(out) :: nxta_asv
        integer, intent(out) :: ipch_asv
        integer, intent(out) :: ipcv_asv
        integer, intent(out) :: jpfc_asv
        integer, intent(out) :: narx_asv
        integer, intent(out) :: ntpr_asv
        character(len=8), intent(out) :: udakey

        integer, intent(out) :: errno

        ! Local variable declarations.
        character(len=56) ux56
        character(len=8) ux8

        errno = 0

        rewind data1

        read (data1) ux8
        if (ux8(1:5) .ne. 'data1') then
            errno = 420
            goto 999
        end if

        read (data1) udakey

        ! Read the array dimension required for chemical elements.
        read (data1) ux56
        read (data1) ncta_asv

        ! Read the array dimension required for basis species.
        read (data1) ux56
        read (data1) nbta_asv

        ! Read the array dimension required for total species.
        read (data1) ux56
        read (data1) nsta_asv

        ! Read the array dimension required for total phases.
        read (data1) ux56
        read (data1) npta_asv

        ! Read the array dimension required for aqueous species.
        read (data1) ux56
        read (data1) nata_asv

        ! Read the array dimension required for pure minerals.
        read (data1) ux56
        read (data1) nmta_asv

        ! Read the array dimension required for pure liquids.
        read (data1) ux56
        read (data1) nlta_asv

        ! Read the array dimension required for gas species.
        read (data1) ux56
        read (data1) ngta_asv

        ! Read the array dimension required for solid-solution phases.
        read (data1) ux56
        read (data1) nxta_asv

        ! Read the array dimension required for solid-solution components
        ! (maximum number per solid solution).
        read (data1) ux56
        read (data1) ikta_asv

        ! Read the array dimension required for the data file title.
        read (data1) ux56
        read (data1) ntid_asv

        ! Read the array dimension required for the temperature ranges in the logK
        ! temperature grid.
        read (data1) ux56
        read (data1) ntpr_asv

        ! Read the array dimension required for the points in a temperature range
        ! on the logK temperature grid.
        read (data1) ux56
        read (data1) narx_asv

        ! Read the array dimension required for the dH/dP order represented on the
        ! data file.
        read (data1) ux56
        read (data1) ipch_asv

        ! Read the array dimension required for the dV/dP order represented on the
        ! data file.
        read (data1) ux56
        read (data1) ipcv_asv

        ! Read the array dimensions for parameters needed for activity coefficient
        ! models.
        if (udakey(1:8) .eq. 'Pitzer  ') then
            ! Read the array dimension required for the sets of Pitzer alpha
            ! coefficients.
            read (data1) ux56
            read (data1) napa_asv

            ! Read the array dimension required for the set of Pitzer S-lambda
            ! coefficients.
            read (data1) ux56
            read (data1) nslta_asv

            ! Read the array dimension required for the set of Pitzer mu
            ! coefficients.
            read (data1) ux56
            read (data1) nmuta_asv

            ! Read the number of coefficients for the Pitzer parameter temperature
            ! function.
            read (data1) ux56
            read (data1) jpfc_asv
        else
            ! Minimum values.
            napa_asv = 1
            nslta_asv = 1
            nmuta_asv = 1
            jpfc_asv = 1
        end if

        ! Set the number of parameters in a Pitzer alpha set.
        if (udakey(1:8) .eq. 'Pitzer  ') then
            ipbt_asv = 2
        else
            ipbt_asv = 1
        end if

        ux8 = ux56(1:8)

        999 continue
    end subroutine indath

    !> Read the body of a data1 file.
    !!
    !! This must be called after `indath`, which positions the file and provides the allocation
    !! sizes (`*_asv`) with which the arrays must be dimensioned. The title, the temperature grid,
    !! the chemical elements, and the interpolating polynomials for the pressure, the parameters of
    !! the activity coefficient model and the "Eh" reaction (2 H2O(l) = 2 O2(g) + 4 H+ + 4 e-) are
    !! read first. The species superblocks are then read with `indats` (aqueous species, pure
    !! minerals and gas species) and `indatp` (solid solutions), and water is cloned as the only
    !! pure liquid with `clones`. Finally, the basis set is resolved with `dfbasp`, and the species
    !! parameters of the activity coefficient model are read with `inbdot` (`SEDH`) or `inupt`
    !! (`Pitzer`).
    !!
    !! Outputs specific to one activity coefficient model are only read for data files using that
    !! model; some are zeroed first, while the rest are left as passed in. The enthalpy and volume
    !! functions are only read if they are represented on the data file (`ipch` and `ipcv` are
    !! non-negative).
    !!
    !! Species and phase indices are 1-based. An empty range is indicated either by a start index of
    !! 0 or by a start index greater than the end index.
    !!
    !! @param[in]  nad1      The logical unit of the data1 file, as positioned by `indath`
    !! @param[out] aadh      The polynomial coefficients for the Debye-Huckel A(gamma,10) parameter,
    !!                       by temperature range (`SEDH` data files only)
    !! @param[out] aadhh     The polynomial coefficients for the Debye-Huckel A(H) parameter, by
    !!                       temperature range
    !! @param[out] aadhv     The polynomial coefficients for the Debye-Huckel A(V) parameter, by
    !!                       temperature range
    !! @param[out] aaphi     The polynomial coefficients for the Debye-Huckel A(phi) parameter, by
    !!                       temperature range (`Pitzer` data files only)
    !! @param[out] abdh      The polynomial coefficients for the Debye-Huckel B parameter, by
    !!                       temperature range (`SEDH` data files only)
    !! @param[out] abdhh     The polynomial coefficients for the Debye-Huckel B(H) parameter, by
    !!                       temperature range (`SEDH` data files only)
    !! @param[out] abdhv     The polynomial coefficients for the Debye-Huckel B(V) parameter, by
    !!                       temperature range (`SEDH` data files only)
    !! @param[out] abdot     The polynomial coefficients for the Helgeson (1969) B-dot parameter, by
    !!                       temperature range (`SEDH` data files only)
    !! @param[out] abdoth    The polynomial coefficients for the B-dot(H) parameter, by temperature
    !!                       range (`SEDH` data files only)
    !! @param[out] abdotv    The polynomial coefficients for the B-dot(V) parameter, by temperature
    !!                       range (`SEDH` data files only)
    !! @param[out] adadhh    The polynomial coefficients for the pressure derivatives of the
    !!                       Debye-Huckel A(H) parameter, by temperature range and order
    !! @param[out] adadhv    The polynomial coefficients for the pressure derivatives of the
    !!                       Debye-Huckel A(V) parameter, by temperature range and order
    !! @param[out] adbdhh    The polynomial coefficients for the pressure derivatives of the
    !!                       Debye-Huckel B(H) parameter, by temperature range and order (`SEDH`
    !!                       data files only)
    !! @param[out] adbdhv    The polynomial coefficients for the pressure derivatives of the
    !!                       Debye-Huckel B(V) parameter, by temperature range and order (`SEDH`
    !!                       data files only)
    !! @param[out] adbdth    The polynomial coefficients for the pressure derivatives of the
    !!                       B-dot(H) parameter, by temperature range and order (`SEDH` data files
    !!                       only)
    !! @param[out] adbdtv    The polynomial coefficients for the pressure derivatives of the
    !!                       B-dot(V) parameter, by temperature range and order (`SEDH` data files
    !!                       only)
    !! @param[out] adhfe     The polynomial coefficients for the pressure derivatives of the
    !!                       enthalpy of the "Eh" reaction, by temperature range and order
    !! @param[out] adhfsa    The polynomial coefficients for the pressure derivatives of the
    !!                       enthalpy function of each species, by temperature range and order
    !! @param[out] advfe     The polynomial coefficients for the pressure derivatives of the volume
    !!                       of the "Eh" reaction, by temperature range and order
    !! @param[out] advfsa    The polynomial coefficients for the pressure derivatives of the volume
    !!                       function of each species, by temperature range and order
    !! @param[out] amua      The coefficients of the temperature function of the Pitzer mu parameter
    !!                       of each triplet (`Pitzer` data files only; zeroed otherwise)
    !! @param[out] aprehw    The polynomial coefficients for the recommended pressure envelope
    !!                       half-width (bars), by temperature range (read only if `ipcv` is
    !!                       non-negative)
    !! @param[out] apresg    The polynomial coefficients for the standard grid pressure (bars), e.g.
    !!                       on the 1 atm-steam saturation curve, by temperature range
    !! @param[out] apxa      The interaction coefficients for the activity coefficients of each
    !!                       solid solution
    !! @param[out] aslma     The coefficients of the temperature functions of the Pitzer
    !!                       S-lambda(0), S-lambda(1), ... parameters of each pair (`Pitzer` data
    !!                       files only; zeroed otherwise)
    !! @param[out] atwta     The atomic weights of the chemical elements
    !! @param[out] axhfe     The polynomial coefficients for the enthalpy of the "Eh" reaction, by
    !!                       temperature range
    !! @param[out] axhfsa    The polynomial coefficients for the enthalpy function of each species,
    !!                       by temperature range
    !! @param[out] axlke     The polynomial coefficients for the log K of the "Eh" reaction, by
    !!                       temperature range
    !! @param[out] axlksa    The polynomial coefficients for the log K of the reaction of each
    !!                       species, by temperature range (zero for basis species)
    !! @param[out] axvfe     The polynomial coefficients for the volume of the "Eh" reaction, by
    !!                       temperature range
    !! @param[out] axvfsa    The polynomial coefficients for the volume function of each species, by
    !!                       temperature range
    !! @param[out] azeroa    The hard core diameters (10^-8 cm) of the aqueous species (`SEDH` data
    !!                       files only; zeroed otherwise)
    !! @param[out] bpxa      The site-mixing parameters for the activity coefficients of each solid
    !!                       solution
    !! @param[out] cco2      The coefficients of the Drummond (1981) equation for the activity
    !!                       coefficient of CO2(aq) (`SEDH` data files only)
    !! @param[out] cdrsa     The reaction coefficients of all species, indexed by `ndrsra`
    !! @param[out] cessa     The elemental composition coefficients of all species, indexed by
    !!                       `nessra`
    !! @param[in]  iapxa_asv The maximum number of interaction coefficients for any solid solution
    !! @param[out] iapxta    The number of interaction coefficients of each solid solution
    !! @param[out] iaqsla    The index of the aqueous solution phase (always 1)
    !! @param[in]  ibpxa_asv The maximum number of site-mixing parameters for any solid solution
    !! @param[out] ibpxta    The number of site-mixing parameters of each solid solution
    !! @param[out] ielam     The E-lambda flag: -1 if E-lambda terms are not used, and 0 if they are
    !!                       (`Pitzer` data files only)
    !! @param[out] igas      The index of the gas phase
    !! @param[in]  ikta_asv  The maximum number of end-member component species in any solid
    !!                       solution
    !! @param[out] insgfa    The flag for the activity coefficient of each electrically neutral
    !!                       aqueous species: 0 sets the log activity coefficient to zero, and -1
    !!                       uses the Drummond (1981) polynomial (`SEDH` data files only; zeroed
    !!                       otherwise)
    !! @param[in]  ipbt_asv  The maximum number of Pitzer alpha parameters for any species pair
    !! @param[out] ipch      The order of the pressure corrections to enthalpy functions; negative
    !!                       if enthalpy functions are not represented
    !! @param[in]  ipch_asv  The maximum order of the pressure corrections to enthalpy functions
    !! @param[out] ipcv      The order of the pressure corrections to volume functions; negative if
    !!                       volume functions are not represented
    !! @param[in]  ipcv_asv  The maximum order of the pressure corrections to volume functions
    !! @param[out] ixrn1a    The index of the first solid-solution phase
    !! @param[out] ixrn2a    The index of the last solid-solution phase
    !! @param[out] jpdblo    The Pitzer data block organization flag; -1 for the classical
    !!                       organization (`Pitzer` data files only)
    !! @param[in]  jpfc_asv  The number of coefficients in the Pitzer parameter temperature function
    !! @param[out] jptffl    The Pitzer parameter temperature function flag (`Pitzer` data files
    !!                       only)
    !! @param[out] jsola     The activity coefficient model flag of each solid solution
    !! @param[out] mwtspa    The molecular weights of the species
    !! @param[out] nalpaa    The index in `palpaa` of the set of alpha coefficients of each S-lambda
    !!                       pair (`Pitzer` data files only)
    !! @param[in]  napa_asv  The maximum number of distinct sets of Pitzer alpha parameters
    !! @param[out] napta     The number of distinct sets of Pitzer alpha parameters (`Pitzer` data
    !!                       files only)
    !! @param[out] narn1a    The index of the first aqueous species (always 1)
    !! @param[out] narn2a    The index of the last aqueous species
    !! @param[in]  narx_asv  The maximum number of coefficients per temperature range
    !! @param[out] narxt     The number of coefficients in each temperature range
    !! @param[out] nata      The number of aqueous species
    !! @param[in]  nata_asv  The maximum number of aqueous species
    !! @param[out] nbaspa    The species index of each basis species
    !! @param[out] nbta      The number of basis species
    !! @param[in]  nbta_asv  The maximum number of basis species
    !! @param[in]  nbtafd    The number of leading species on the data file that are basis species;
    !!                       those among them with a reaction (auxiliary basis species) are added to
    !!                       the basis set
    !! @param[in]  nbta1_asv The maximum number of species in a reaction, i.e. `nbta_asv + 1`
    !! @param[out] ncmpra    The indices of the first and last species of each phase
    !! @param[out] ncta      The number of chemical elements (set to `ncta_asv`)
    !! @param[in]  ncta_asv  The number of chemical elements
    !! @param[out] ndrsa     The species index of each reaction coefficient in `cdrsa` (0 for the
    !!                       null species of a basis species)
    !! @param[in]  ndrsa_asv The size of `cdrsa` and `ndrsa`
    !! @param[out] ndrsra    The indices in `cdrsa` and `ndrsa` of the first and last coefficients
    !!                       of the reaction of each species
    !! @param[out] nessa     The element index of each composition coefficient in `cessa` (0 for the
    !!                       null element of a species with no elements)
    !! @param[in]  nessa_asv The size of `cessa` and `nessa`
    !! @param[out] nessra    The indices in `cessa` and `nessa` of the first and last coefficients
    !!                       of the composition of each species
    !! @param[out] ngrn1a    The index of the first gas species
    !! @param[out] ngrn2a    The index of the last gas species
    !! @param[out] ngta      The number of gas species
    !! @param[out] nlrn1a    The index of the first pure liquid (water), or 0 if water is not the
    !!                       first aqueous species
    !! @param[out] nlrn2a    The index of the last pure liquid (water), or 0 if water is not the
    !!                       first aqueous species
    !! @param[out] nlta      The number of pure liquids: 1, or 0 if water is not the first aqueous
    !!                       species
    !! @param[out] nmrn1a    The index of the first pure mineral, or 0 if there are none
    !! @param[out] nmrn2a    The index of the last pure mineral
    !! @param[out] nmta      The number of pure minerals
    !! @param[out] nmuta     The number of triplets for which Pitzer mu coefficients are defined
    !!                       (`Pitzer` data files only)
    !! @param[in]  nmuta_asv The maximum number of triplets for which Pitzer mu coefficients are
    !!                       defined
    !! @param[out] nmuxa     The species indices of each mu triplet (`Pitzer` data files only)
    !! @param[out] npta      The number of phases
    !! @param[in]  npta_asv  The maximum number of phases
    !! @param[out] nslta     The number of pairs for which Pitzer S-lambda coefficients are defined
    !!                       (`Pitzer` data files only)
    !! @param[in]  nslta_asv The maximum number of pairs for which Pitzer S-lambda coefficients are
    !!                       defined
    !! @param[out] nslxa     The species indices of each S-lambda pair (`Pitzer` data files only)
    !! @param[out] nsta      The number of species, including clones
    !! @param[in]  nsta_asv  The maximum number of species
    !! @param[in]  ntid_asv  The maximum number of lines in the data file title
    !! @param[out] ntitld    The number of title lines read, including the terminator line, if any
    !! @param[in]  ntpr_asv  The maximum number of temperature ranges
    !! @param[out] ntprt     The number of temperature ranges
    !! @param[out] nxrn1a    The index of the first solid-solution end member
    !! @param[out] nxrn2a    The index of the last solid-solution end member
    !! @param[out] nxta      The number of solid solutions
    !! @param[in]  nxta_asv  The maximum number of solid solutions
    !! @param[out] qclnsa    Whether each species was created by cloning
    !! @param[out] palpaa    The distinct sets of Pitzer alpha coefficients (`Pitzer` data files
    !!                       only; zeroed otherwise)
    !! @param[out] tdamax    The nominal maximum temperature (C) of the data file
    !! @param[out] tdamin    The nominal minimum temperature (C) of the data file
    !! @param[out] tempcu    The maximum temperature (C) of each temperature range
    !! @param[out] ubasp     The names of the basis species, including their phase names
    !! @param[in]  udakey    The activity coefficient model keystring, as read by `indath`
    !! @param[out] udatfi    The three-letter identifier of the data file (e.g. `com`), taken from
    !!                       the first title line beginning with `data0.`, or `current` if there is
    !!                       none
    !! @param[out] uelema    The names of the chemical elements
    !! @param[out] uspeca    The names of the species; the first 24 characters are the species name,
    !!                       and the last 24 the name of its phase
    !! @param[out] uphasa    The names of the phases
    !! @param[out] uptypa    The type of each phase: `Aqueous solution`, `Solid`, `Liquid` or `Gas`
    !! @param[out] utitld    The lines of the data file title
    !! @param[out] vosp0a    The molar volumes of the species, which are not read, and so are zero
    !! @param[out] zchara    The electrical charges of the species
    !! @param[out] errno     The number of errors found while reading the species, solid solutions
    !!                       and activity coefficient model parameters, including one if water is
    !!                       not the first aqueous species
    subroutine indata(nad1, aadh, aadhh, aadhv, aaphi, abdh, abdhh, abdhv, abdot, &
                      abdoth, abdotv, adadhh, adadhv, adbdhh, adbdhv, adbdth, &
                      adbdtv, adhfe, adhfsa, advfe, advfsa, amua, aprehw, apresg, &
                      apxa, aslma, atwta, axhfe, axhfsa, axlke, axlksa, axvfe, &
                      axvfsa, azeroa, bpxa, cco2, cdrsa, cessa, iapxa_asv, &
                      iapxta, iaqsla, ibpxa_asv, ibpxta, ielam, igas, ikta_asv, &
                      insgfa, ipbt_asv, ipch, ipch_asv, ipcv, ipcv_asv, ixrn1a, &
                      ixrn2a, jpdblo, jpfc_asv, jptffl, jsola, mwtspa, nalpaa, &
                      napa_asv, napta, narn1a, narn2a, narx_asv, narxt, nata, &
                      nata_asv, nbaspa, nbta, nbta_asv, nbtafd, nbta1_asv, ncmpra, &
                      ncta, ncta_asv, ndrsa, ndrsa_asv, ndrsra, nessa, nessa_asv, &
                      nessra, ngrn1a, ngrn2a, ngta, nlrn1a, nlrn2a, &
                      nlta, nmrn1a, nmrn2a, nmta, nmuta, &
                      nmuta_asv, nmuxa, npta, npta_asv, nslta, nslta_asv, nslxa, &
                      nsta, nsta_asv, ntid_asv, ntitld, ntpr_asv, ntprt, nxrn1a, &
                      nxrn2a, nxta, nxta_asv, qclnsa, palpaa, tdamax, tdamin, &
                      tempcu, ubasp, udakey, udatfi, uelema, uspeca, uphasa, &
                      uptypa, utitld, vosp0a, zchara, errno)
        ! Calling sequence variable declarations.
        integer iapxa_asv,ibpxa_asv,ikta_asv,ipbt_asv,ipch_asv,ipcv_asv
        integer jpfc_asv,napa_asv,narx_asv,nata_asv,nbta_asv,nbta1_asv,ncta_asv
        integer ndrsa_asv,nessa_asv,nmuta_asv
        integer npta_asv,nslta_asv,nsta_asv,ntid_asv,ntpr_asv,nxta_asv

        integer nad1, errno

        integer iapxta(nxta_asv),ibpxta(nxta_asv),insgfa(nata_asv)
        integer jsola(nxta_asv),nalpaa(nslta_asv),narxt(ntpr_asv)
        integer nbaspa(nbta_asv),ncmpra(2,npta_asv),ndrsa(ndrsa_asv)
        integer ndrsra(2,nsta_asv),nessa(nessa_asv),nessra(2,nsta_asv)
        integer nmuxa(3,nmuta_asv),nslxa(2,nslta_asv)

        integer iaqsla,ielam,igas,ipch,ipcv,ixrn1a,ixrn2a,jpdblo,jptffl
        integer napta,narn1a,narn2a,nata,nbta,nbtafd,ncta,ngrn1a,ngrn2a,ngta
        integer nlrn1a,nlrn2a,nlta,nmrn1a,nmrn2a,nmta,nmuta,npta,nslta,nsta
        integer ntitld,ntprt,nxrn1a,nxrn2a,nxta

        logical qclnsa(nsta_asv)

        character(len=8) uelema(ncta_asv)
        character(len=24) uphasa(npta_asv),uptypa(npta_asv)
        character(len=48) ubasp(nbta_asv),uspeca(nsta_asv)
        character(len=80) utitld(ntid_asv)

        character(len=8) udakey,udatfi

        real(8) tempcu(ntpr_asv)

        real(8) aadh(narx_asv,ntpr_asv),aadhh(narx_asv,ntpr_asv)
        real(8) aadhv(narx_asv,ntpr_asv),aaphi(narx_asv,ntpr_asv)
        real(8) abdh(narx_asv,ntpr_asv),abdhh(narx_asv,ntpr_asv)
        real(8) abdhv(narx_asv,ntpr_asv),abdot(narx_asv,ntpr_asv)
        real(8) abdoth(narx_asv,ntpr_asv),abdotv(narx_asv,ntpr_asv)
        real(8) adadhh(narx_asv,ntpr_asv,ipch_asv)
        real(8) adadhv(narx_asv,ntpr_asv,ipcv_asv)
        real(8) adbdhh(narx_asv,ntpr_asv,ipch_asv)
        real(8) adbdhv(narx_asv,ntpr_asv,ipcv_asv)
        real(8) adbdth(narx_asv,ntpr_asv,ipch_asv)
        real(8) adbdtv(narx_asv,ntpr_asv,ipcv_asv)
        real(8) adhfe(narx_asv,ntpr_asv,ipch_asv)
        real(8) advfe(narx_asv,ntpr_asv,ipcv_asv)
        real(8) adhfsa(narx_asv,ntpr_asv,ipch_asv,nsta_asv)
        real(8) advfsa(narx_asv,ntpr_asv,ipcv_asv,nsta_asv)
        real(8) aprehw(narx_asv,ntpr_asv),apresg(narx_asv,ntpr_asv)
        real(8) apxa(iapxa_asv,nxta_asv),atwta(ncta_asv)
        real(8) axhfe(narx_asv,ntpr_asv),axhfsa(narx_asv,ntpr_asv,nsta_asv)
        real(8) axlke(narx_asv,ntpr_asv),axlksa(narx_asv,ntpr_asv,nsta_asv)
        real(8) axvfe(narx_asv,ntpr_asv),axvfsa(narx_asv,ntpr_asv,nsta_asv)

        real(8) amua(jpfc_asv,nmuta_asv)
        real(8) aslma(jpfc_asv,0:ipbt_asv,nslta_asv),azeroa(nata_asv)
        real(8) bpxa(ibpxa_asv,nxta_asv),cco2(5),cdrsa(ndrsa_asv)
        real(8) cessa(nessa_asv),mwtspa(nsta_asv),palpaa(ipbt_asv,napa_asv)
        real(8) vosp0a(nsta_asv),zchara(nsta_asv)

        real(8) tdamax,tdamin

        character(len=24), dimension(:), allocatable :: udrsv
        character(len=8), dimension(:), allocatable :: uessv

        real(8), dimension(:), allocatable :: cdrsv,cessv

        integer ipc,n,nc,ndrsn,nessn,nmax,np,ns,nsc,ntpr,nwatra

        logical qx

        character(len=80) ux80
        character(len=56) ux56
        character(len=24) uphasv,uwater,uaqsln,uptsld,uptliq,uptgas,usblkf,ux24
        character(len=8) uendit,usedh,upitz,ustr,ustr2,ustr3,uterm

        data uwater /'H2O                     '/
        data uaqsln /'Aqueous solution        '/
        data uptsld /'Solid                   '/
        data uptliq /'Liquid                  '/
        data uptgas /'Gas                     '/

        data uendit /'endit.  '/,uterm  /'+-------'/
        data usedh  /'SEDH    '/,upitz  /'Pitzer  '/

        ALLOCATE(cessv(ncta_asv))
        ALLOCATE(uessv(ncta_asv))

        ALLOCATE(cdrsv(nbta1_asv))
        ALLOCATE(udrsv(nbta1_asv))

        ! Zero some arrays.
        nmax = nbta_asv
        call initiz(nbaspa,nmax)

        nmax = ndrsa_asv
        call initiz(ndrsa,nmax)
        call initaz(cdrsa,nmax)

        nmax = nsta_asv
        call initaz(vosp0a,nmax)

        nmax = 2*nsta_asv
        call initiz(ndrsra,nmax)

        nmax = narx_asv*ntpr_asv*nsta_asv
        call initaz(axhfsa,nmax)
        call initaz(axlksa,nmax)
        call initaz(axvfsa,nmax)

        nmax = nata_asv
        call initaz(azeroa,nmax)
        call initiz(insgfa,nmax)

        nmax = ipbt_asv*napa_asv
        call initaz(palpaa,nmax)
        nmax = jpfc_asv*(ipbt_asv + 1)*nslta_asv
        call initaz(aslma,nmax)
        nmax = jpfc_asv*nmuta_asv
        call initaz(amua,nmax)

        ! Don't rewind the DATA1 file (nad1). It should be positioned properly by
        ! the preceding call to subroutine indath.f.

        ! Initialize the error counter.
        errno = 0

        ! Set the number of elements on the data file. This equal to the dimensioned
        ! limit. Note that nbta, the number of basis species, is determined in this
        ! subroutine as it is not usually equal to the corresponding dimensioned
        ! limit nbta_asv. In fact, nbta as returned by the subroutine may be
        ! subsequently increased due to "promotions" implied by the contents of the
        ! input file.

        ncta = ncta_asv

        ! Read the data file title.
        ntitld = 0
        do n = 1,ntid_asv
            read (nad1) utitld(n)
            ntitld = ntitld + 1
            if (utitld(n)(1:8) .eq. uterm(1:8)) go to 140
        end do
        140 continue

        ! Search the data file title for the usual identifying three-letter
        ! keystring (e.g., com, hmw, etc.).
        udatfi = 'current'
        do n = 1,ntitld
            ux80 = utitld(n)
            call lejust(ux80)
            if (ux80(1:6) .eq. 'data0.') then
                udatfi = ux80(7:9)
                go to 170
            end if
        end do
        170 continue

        ! Read the actual number of temperature ranges in the temperature grid.
        read (nad1) ux56
        read (nad1) ntprt

        ! Read the actual number of coefficients in each range.
        do ntpr = 1,ntprt
            read (nad1) ux56
            read (nad1) narxt(ntpr)
        end do

        ! Read a flag indicating the degree of representation of enthalpy functions.
        read (nad1) ux56
        read (nad1) ipch

        ! Read a flag indicating the degree of representation of volume functions.
        read (nad1) ux56
        read (nad1) ipcv

        if (udakey(1:8) .eq. upitz(1:8)) then
            ! Read the Pitzer data block organization flag.
            read (nad1) ux56
            read (nad1) jpdblo

            ! Read the Pitzer parameter temperature function flag.
            read (nad1) ux56
            read (nad1) jptffl
        end if

        ! Read chemical elements data.
        read (nad1) ux24

        do nc = 1,ncta
            read (nad1) uelema(nc),atwta(nc)
        end do

        ! Read nominal temperature limits (Celsius) for the data file.
        read (nad1) ux56
        read (nad1) tdamin,tdamax

        ! Read the maximum temperatures (tempcu) of the temperature ranges. These
        ! are used to find the temperature range flag (ntpr) for any specified
        ! temperature (see EQLIB/gntpr.f).
        read (nad1) ux56
        do n = 1,ntprt
            read (nad1) tempcu(n)
        end do

        ! Read interpolating polynomial coefficients for computing the standard grid
        ! pressure (bars) as a function of temperature (Celsius). Often this grid
        ! corresponds to 1.013 bar up to 100C and the steam-liquid water saturation
        ! pressure at higher temperatures.
        !
        ! Calling sequence substitutions:
        !   apresg for arr
        call indatc(nad1,apresg,narx_asv,narxt,ntpr_asv,ntprt,ux24)

        if (ipcv .ge. 0) then
            ! Read interpolating polynomial coefficients for computing the
            ! recommended pressure envelope half width (bars).
            !
            ! Calling sequence substitutions:
            !   aprehw for arr
            call indatc(nad1,aprehw,narx_asv,narxt,ntpr_asv,ntprt,ux24)
        end if

        if (udakey(1:8) .eq. usedh(1:8)) then
            ! The aqeuous species activity coefficient formalism is consistent with
            ! the B-dot equation, the Davies equation, or similar equations.

            ! Read interpolating polynomial coefficients for the Debye-Huckel
            ! A(gamma,10) parameter and related parameters.
            !
            ! Calling sequence substitutions:
            !   aadh for arr
            call indatc(nad1,aadh,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            if (ipch .ge. 0) then
                ! Calling sequence substitutions:
                !   aadhh for arr
                call indatc(nad1,aadhh,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipch
                    ! Calling sequence substitutions:
                    !   adadhh for arr
                    !   ipch_asv for ipcx_asv
                    call indatd(nad1,adadhh,ipc,ipch_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            if (ipcv .ge. 0) then
                ! Calling sequence substitutions:
                !   aadhv for arr
                call indatc(nad1,aadhv,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipcv
                    ! Calling sequence substitutions:
                    !   adadhv for arr
                    !   ipcv_asv for ipcx_asv
                    call indatd(nad1,adadhv,ipc,ipcv_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            ! Read interpolating polynomial coefficients for the Debye-Huckel
            ! B(gamma) and related parameters.
            ! Calling sequence substitutions:
            !   abdh for arr
            call indatc(nad1,abdh,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            if (ipch .ge. 0) then
                ! Calling sequence substitutions:
                !   abdhh for arr
                call indatc(nad1,abdhh,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipch
                    ! Calling sequence substitutions:
                    !   adbdhh for arr
                    !   ipch_asv for ipcx_asv

                    call indatd(nad1,adbdhh,ipc,ipch_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            if (ipcv .ge. 0) then
                ! Calling sequence substitutions:
                !   abdhv for arr
                call indatc(nad1,abdhv,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipcv
                    ! Calling sequence substitutions:
                    !   adbdhv for arr
                    !   ipcv_asv for ipcx_asv
                    call indatd(nad1,adbdhv,ipc,ipcv_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            ! Read interpolating polynomial coefficients for the B-dot parameter and
            ! related parameters.
            !
            ! Calling sequence substitutions:
            !   abdot for arr
            call indatc(nad1,abdot,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            if (ipch .ge. 0) then
                ! Calling sequence substitutions:
                !   abdoth for arr
                call indatc(nad1,abdoth,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipch
                    ! Calling sequence substitutions:
                    !   adbdth for arr
                    !   ipch_asv for ipcx_asv
                    call indatd(nad1,adbdth,ipc,ipch_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            if (ipcv .ge. 0) then
                ! Calling sequence substitutions:
                !   abdotv for arr
                call indatc(nad1,abdotv,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipcv
                    ! Calling sequence substitutions:
                    !   adbdtv for arr
                    !   ipcv_asv for ipcx_asv
                    call indatd(nad1,adbdtv,ipc,ipcv_asv,narxt,narx_asv,ntprt, &
                                ntpr_asv,ux24)
                end do
            end if

            ! Read coefficients for the Drummond (1981) equation. This equation
            ! represents the activity coefficient of CO2(aq) as a function of
            ! temperature and ionic strength in sodium chloride solutions.
            read (nad1) ux24
            read (nad1) (cco2(n), n = 1,5)
        end if

        if (udakey(1:8) .eq. upitz(1:8)) then
            ! The aqeuous species activity coefficient formalism is consistent with
            ! Pitzer's equations. Read interpolating polynomial coefficients for
            ! Debye-Huckel A(phi) and related parameters.
            !
            ! Calling sequence substitutions:
            !   aaphi for arr
            call indatc(nad1,aaphi,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            if (ipch .ge. 0) then
                ! Calling sequence substitutions:
                !   aadhh for arr
                call indatc(nad1,aadhh,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipch
                    ! Calling sequence substitutions:
                    !   adadhh for arr
                    !   ipch_asv for ipcx_asv
                    call indatd(nad1,adadhh,ipc,ipch_asv,narxt,narx_asv,ntprt,&
                                ntpr_asv,ux24)
                end do
            end if

            if (ipcv .ge. 0) then
                ! Calling sequence substitutions:
                !   aadhv for arr
                call indatc(nad1,aadhv,narx_asv,narxt,ntpr_asv,ntprt,ux24)

                do ipc = 1,ipcv
                    ! Calling sequence substitutions:
                    !   adadhv for arr
                    !   ipcv_asv for ipcx_asv
                    call indatd(nad1,adadhv,ipc,ipcv_asv,narxt,narx_asv,ntprt,&
                                ntpr_asv,ux24)
                end do
            end if
        end if

        ! Read interpolating polynomial coefficients for the log K of the "Eh"
        ! reaction:
        !
        !   2 H2O(l) = 2 O2(g) + 4 H+ + 4 e-
        !
        ! Calling sequence substitutions:
        !   axlke for arr
        call indatc(nad1,axlke,narx_asv,narxt,ntpr_asv,ntprt,ux24)

        if (ipch .ge. 0) then
            ! Calling sequence substitutions:
            !   axhfe for arr
            call indatc(nad1,axhfe,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            do ipc = 1,ipch
                ! Calling sequence substitutions:
                !   adhfe for arr
                !   ipch_asv for ipcx_asv
                call indatd(nad1,adhfe,ipc,ipch_asv,narxt,narx_asv,ntprt,&
                            ntpr_asv,ux24)
            end do
        end if

        if (ipcv .ge. 0) then
            ! Calling sequence substitutions:
            !   axvfe for arr
            call indatc(nad1,axvfe,narx_asv,narxt,ntpr_asv,ntprt,ux24)

            do ipc = 1,ipcv
                ! Calling sequence substitutions:
                !   advfe for arr
                !   ipcv_asv for ipcx_asv
                call indatd(nad1,advfe,ipc,ipcv_asv,narxt,narx_asv,ntprt,&
                            ntpr_asv,ux24)
            end do
        end if

        ! Read the phases and species and associated data from the data file. The
        ! following variables are used as counters:
        !
        !  np     = phase index
        !  ns     = species index

        ! Initialize the qclnsa array to .false.
        qx = .false.
        call initlv(qclnsa,nsta_asv,qx)

        ! Initialize the following variables, all of which are used below as
        ! counters.
        !
        !   nessn  = counter for the cessa and nessa arrays
        !   ndrsn  = counter for the cdrsa and ndrsa arrays
        !   ns     = species index
        !   nbta   = number of basis species
        !   nata   = number of aqueous species
        !   ngta   = number of gas species
        !   nmta   = number of pure mineral species
        !   nlta   = number of pure liquid species
        !   nxta   = number of solid solution phases

        nessn = 0
        ndrsn = 0
        ns = 0
        nbta = 0
        nata = 0
        ngta = 0
        nmta = 0
        nlta = 0
        nxta = 0

        ! Process the aqueous species superblock. Set up the aqueous solution as the
        ! first phase.
        np = 1
        uphasv(1:24) = uaqsln(1:24)
        iaqsla = np
        uphasa(np)(1:24) = uphasv(1:24)
        uptypa(np)(1:24) = uaqsln(1:24)
        usblkf(1:24) = uaqsln(1:24)
        ncmpra(1,1) = 1
        narn1a = 1

        ! Read the superblock header.
        read (nad1) ustr,ustr2,ustr3

        ! Read the blocks in the current superblock.
        call indats(adhfsa, advfsa, axhfsa, axlksa, axvfsa, cdrsa, cdrsv, cessa, &
                    cessv, ipch, ipch_asv, ipcv, ipcv_asv, mwtspa, nad1, narxt, &
                    narx_asv, nata, nbta, nbta_asv, nbta1_asv, nbtafd, &
                    ncmpra, ncta, ncta_asv, ndrsa, ndrsa_asv, ndrsn, ndrsra, &
                    errno, nessa, nessa_asv, nessn, nessra, ngta, nlta, &
                    nmta, np, npta_asv, ns, nsta_asv, ntprt, &
                    ntpr_asv, uaqsln, ubasp, udrsv, uelema, uendit, uessv, uphasa, &
                    uphasv, uptgas, uptliq, uptsld, uptypa, usblkf, uspeca, &
                    vosp0a, zchara)

        ncmpra(2,np) = ns
        narn2a = ns

        ! Check to see that water is the first species in the phase "aqueous
        ! solution". This is required so that all solute species can be cleanly
        ! referenced in simple loop; that is, in a loop of the form
        ! "do ns = narn1a + 1,narn2a".
        nwatra = 0
        if (uspeca(narn1a)(1:24) .eq. uwater(1:24)) nwatra = 1

        if (nwatra .eq. 0) then
            errno = errno + 1
        end if

        ! Process the pure minerals superblock. Each pure mineral is both a species
        ! and a phase. The phase name variable uphasv will be set to the name of
        ! each mineral as its block is read.
        usblkf(1:24) = uptsld(1:24)
        nmrn1a = ns + 1

        ! Read the superblock header.
        read (nad1) ustr,ustr2,ustr3

        ! Read the blocks in the current superblock.
        call indats(adhfsa, advfsa, axhfsa, axlksa, axvfsa, cdrsa, cdrsv, cessa, &
                    cessv, ipch, ipch_asv, ipcv, ipcv_asv, mwtspa, nad1, narxt, &
                    narx_asv, nata, nbta, nbta_asv, nbta1_asv, nbtafd, &
                    ncmpra, ncta, ncta_asv, ndrsa, ndrsa_asv, ndrsn, ndrsra, &
                    errno, nessa, nessa_asv, nessn, nessra, ngta, nlta, &
                    nmta, np, npta_asv, ns, nsta_asv, ntprt, &
                    ntpr_asv, uaqsln, ubasp, udrsv, uelema, uendit, uessv, uphasa, &
                    uphasv, uptgas, uptliq, uptsld, uptypa, usblkf, uspeca, &
                    vosp0a, zchara)

        nmrn2a = ns
        if (nmrn2a .le. narn2a) nmrn1a = 0

        ! There is presently no superblock corresponding to pure liquids. Set up
        ! water as a pure liquid.
        usblkf(1:24) = uptliq(1:24)
        nlrn1a = 0
        nlrn2a = 0
        nlta = 0

        if (nwatra .gt. 0) then
            np = np + 1
            ns = ns + 1
            uphasv(1:24) = uspeca(nwatra)(1:24)
            uphasa(np)(1:24) = uphasv(1:24)
            uptypa(np)(1:24) = uptliq(1:24)
            ncmpra(1,np) = ns
            ncmpra(2,np) = ns
            nsc = 1
            call clones(axlksa, cdrsa, cessa, mwtspa, narx_asv, ndrsa, ndrsa_asv, &
                        ndrsn, ndrsra, nessa, nessa_asv, nessn, nessra, np, &
                        npta_asv, ns, nsc, nsta_asv, ntpr_asv, uphasa, uspeca, &
                        zchara)
            qclnsa(ns) = .true.
            nlrn1a = ns
            nlrn2a = ns
            nlta = 1
        end if

        ! Process the gas species superblock. Set up the gas phase as the next
        ! phase.
        uphasv(1:24) = uptgas(1:24)
        usblkf(1:24) = uptgas(1:24)
        np = np + 1
        igas = np
        uphasa(np)(1:24) = uphasv(1:24)
        uptypa(np)(1:24) = uptgas(1:24)
        ncmpra(1,np) = ns + 1
        ngrn1a = ns + 1

        ! Read the superblock header.
        read (nad1) ustr,ustr2,ustr3

        ! Read the blocks in the current superblock.
        call indats(adhfsa, advfsa, axhfsa, axlksa, axvfsa, cdrsa, cdrsv, cessa, &
                    cessv, ipch, ipch_asv, ipcv, ipcv_asv, mwtspa, nad1, narxt, &
                    narx_asv, nata, nbta, nbta_asv, nbta1_asv, nbtafd, &
                    ncmpra, ncta, ncta_asv, ndrsa, ndrsa_asv, ndrsn, ndrsra, &
                    errno, nessa, nessa_asv, nessn, nessra, ngta, nlta, &
                    nmta, np, npta_asv, ns, nsta_asv, ntprt, &
                    ntpr_asv, uaqsln, ubasp, udrsv, uelema, uendit, uessv, uphasa, &
                    uphasv, uptgas, uptliq, uptsld, uptypa, usblkf, uspeca, &
                    vosp0a, zchara)

        ngrn2a = ns
        if (ngrn2a .le. nlrn2a) ngrn1a = 0
        ncmpra(2,np) = ns

        ! Process the solid solution superblock.
        read (nad1) ustr,ustr2,ustr3
        nxrn1a = ns + 1
        ixrn1a = np + 1

        call indatp(apxa, axlksa, bpxa, cdrsa, cessa, iapxa_asv, iapxta, &
                    ibpxa_asv, ibpxta, ikta_asv, jsola, mwtspa, nad1, narx_asv, &
                    ncmpra, ndrsa, ndrsa_asv, ndrsn, ndrsra, errno, nessa, &
                    nessa_asv, nessn, nessra, nmrn1a, nmrn2a, np, npta_asv, ns, &
                    nsta_asv, ntpr_asv, nxta, nxta_asv, qclnsa, uendit, uspeca, &
                    uphasa, uptsld, uptypa, zchara)

        npta = np
        nsta = ns
        nxrn2a = ns
        ixrn2a = np
        if (nxrn2a .le. nlrn2a) then
            nxrn1a = 0
            nxrn2a = 0
            ixrn1a = 0
            ixrn2a = 0
        end if

        ! Set up the nbaspa array and expand the elements of the ubasp array to the
        ! full 48 characters. Convert basis species indices in the ndrsa array to
        ! species indices.
        call dfbasp(nbaspa, nbta, nbta_asv, ndrsa, ndrsa_asv, ndrsra, errno, nsta, &
                    nsta_asv, ubasp, uspeca)

        if (udakey(1:8) .eq. usedh(1:8)) then
            ! The aqeuous species activity coefficient formalism is consistent with
            ! the B-dot equation, the Davies equation, or similar equations. Read
            ! the appropriate data for this formalism.
            call inbdot(azeroa, insgfa, nad1, narn1a, narn2a, nata, nata_asv, &
                        errno, nsta_asv, uspeca)
        end if

        if (udakey(1:8) .eq. upitz(1:8)) then
            ! The aqeuous species activity coefficient formalism is consistent with
            ! Pitzer's equations. Read the appropriate data for this formalism.
            call inupt(amua, aslma, ielam, ipbt_asv, jpdblo, jpfc_asv, nad1, &
                       nalpaa, napa_asv, napta, narn1a, narn2a, errno, nmuta, &
                       nmuta_asv, nmuxa, nslta, nslta_asv, nslxa, nsta_asv, &
                       palpaa, uspeca, zchara)
        end if

        DEALLOCATE(cessv)
        DEALLOCATE(uessv)
        DEALLOCATE(cdrsv)
        DEALLOCATE(udrsv)
    end subroutine indata

    !> Read the B-dot model parameters of the aqueous species.
    !!
    !! For each aqueous solute species, these are its hard core diameter (`azeroa`) and its neutral
    !! species flag (`insgfa`). The latter is relevant only for electrically neutral species: if it
    !! is 0, the log activity coefficient is set to zero, and if it is -1, the log activity
    !! coefficient is represented by the Drummond (1981) polynomial. Water (the solvent) is not
    !! subject to the flag.
    !!
    !! Entries for unknown species are skipped, and for a duplicated species the first entry is
    !! used. Species without an entry are given the default hard core diameter of 4.0 (10^-8 cm).
    !!
    !! @private
    !!
    !! @param[out]    azeroa   The hard core diameter (10^-8 cm) of each aqueous species
    !! @param[out]    insgfa   The neutral species flag of each aqueous species
    !! @param[in]     nad1     The logical unit of the data1 file
    !! @param[in]     narn1a   The index of the first aqueous species
    !! @param[in]     narn2a   The index of the last aqueous species
    !! @param[in]     nata     The number of aqueous species
    !! @param[in]     nata_asv The maximum number of aqueous species
    !! @param[in,out] nerr     The error count; incremented if there are more entries than aqueous
    !!                         species, in which case the rest of the block is not read and no
    !!                         defaults are assigned
    !! @param[in]     nsta_asv The maximum number of species
    !! @param[in]     uspeca   The names of the species
    subroutine inbdot(azeroa,insgfa,nad1,narn1a,narn2a,nata,nata_asv,nerr,nsta_asv,uspeca)
        integer nata_asv,nsta_asv

        integer insgfa(nata_asv)
        integer nad1,narn1a,narn2a,nata,nerr

        character(len=48) uspeca(nsta_asv)

        real(kind=8) azeroa(nata_asv)

        integer igx,j2,na,naz,ncount,ns

        real(kind=8) azdef,azx

        character(len=24) unam,unam1,unam2
        character(len=8) uendit

        data uendit /'endit.  '/

        ! The following variable is the default value for the hard core diameter of
        ! an aqueous solute species. Note that hard core diameters are given in
        ! units of 10**-8 cm.

        data azdef  /4.0/

        ! Initialize the azeroa and insgfa arrays to zero.
        do na = 1,nata_asv
            azeroa(na) = 0.
            insgfa(na) = 0
        end do

        ! Read the block contents.
        naz = 0

        ! Read the species name and azeroa and insgfa data.
        110 read (nad1) unam,azx,igx

        ! Test for the end of the data block.
        if (unam(1:8) .eq. uendit(1:8)) go to 120
            ! Find the species index, ns.
            ! Calling sequence substitutions:
            !     narn1a for nrn1a
            !     narn2a for nrn2a
            call srchn(narn1a,narn2a,ns,nsta_asv,unam,uspeca)

            ! If not found among the loaded species, skip.
            if (ns .le. 0) then
                j2 = ilnobl(unam)
                go to 110
        end if

        ! Compute the aqueous species index na.
        na = ns - narn1a + 1

        ! Test for duplicate input.

        if (azeroa(na) .gt. 0.) then
            go to 110
        end if

        naz = naz + 1
        if (naz .gt. nata) then
            nerr = nerr + 1
            go to 999
        end if

        azeroa(na) = azx
        insgfa(na) = igx
        go to 110

        ! Check for solute species with no entries.
        120 do na = 1,nata
            if (azeroa(na) .le. 0.) go to 140
        end do
        go to 999

        ! Assign the default value if needed.
        140 continue
        ncount = 0
        do ns = narn1a,narn2a
            na = ns - narn1a + 1
            if (azeroa(na) .le. 0.) then
                azeroa(na) = azdef
                if (ns .ne. narn1a) then
                    if (ncount .le. 0) then
                        unam1 = uspeca(ns)(1:24)
                        ncount = 1
                    else
                        unam2 = uspeca(ns)(1:24)
                        j2 = ilnobl(unam2)
                        ncount = 0
                    end if
                end if
            end if
        end do

        if (ncount .eq. 1) then
            j2 = ilnobl(unam1)
        end if
        999 continue
    end subroutine inbdot

    !> Set the first `nmax` elements of a real array to zero.
    !!
    !! @private
    !!
    !! @param[out] array The array
    !! @param[in]  nmax  The number of elements to set
    subroutine initaz(array, nmax)
        integer, intent(in) :: nmax
        real(kind=8), intent(inout) :: array(nmax)

        integer i

        do i = 1,nmax
            array(i) = 0.0
        end do
    end subroutine initaz

    !> Set the first `nmax` elements of an integer array to zero.
    !!
    !! @private
    !!
    !! @param[out] iarray The array
    !! @param[in]  nmax   The number of elements to set
    subroutine initiz(iarray, nmax)
        integer, intent(in) :: nmax
        integer, intent(inout) :: iarray(nmax)

        integer i

        do i = 1,nmax
            iarray(i) = 0
        end do
    end subroutine initiz

    !> Set the first `nmax` elements of a logical array to a value.
    !!
    !! Normally, `nmax` is the size of `qarray`, but it may be smaller. A multidimensional array may
    !! be initialized by passing the product of its dimensions as `nmax`; use caution if `nmax` is
    !! not that product. The loop is unrolled by a factor of 8.
    !!
    !! @private
    !!
    !! @param[out] qarray The array
    !! @param[in]  nmax   The number of elements to set
    !! @param[in]  qvalue The value to which to set the elements
    subroutine initlv(qarray,nmax,qvalue)
        integer nmax

        logical qarray(nmax),qvalue

        integer i,ileft

        logical qv

        qv = qvalue
        ileft = (nmax/8)*8

        do i = 1,ileft,8
            qarray(i) = qv
            qarray(i + 1) = qv
            qarray(i + 2) = qv
            qarray(i + 3) = qv
            qarray(i + 4) = qv
            qarray(i + 5) = qv
            qarray(i + 6) = qv
            qarray(i + 7) = qv
        end do

        do i = ileft + 1,nmax
            qarray(i) = qv
        end do
    end subroutine initlv

    !> Find the position of the last non-blank character of a string.
    !!
    !! @private
    !!
    !! @param[in] ustr The string
    !!
    !! @return The 1-based position of the last non-blank character, or 0 if the string is blank
    integer function ilnobl(ustr)
        character(len=*), intent(in) :: ustr

        integer j, nchars

        nchars = len(ustr)
        ilnobl = 0

        do j = nchars,1,-1
            if (ustr(j:j) .ne. ' ') then
                ilnobl = j
                go to 999
            end if
        end  do

        999 continue
    end function ilnobl

    !> Find the position of the first non-blank character of a string.
    !!
    !! @private
    !!
    !! @param[in] ustr The string
    !!
    !! @return The 1-based position of the first non-blank character, or 0 if the string is blank
    integer function ifnobl(ustr)
        character(len=*) ustr
        integer j, nchars

        nchars = len(ustr)
        ifnobl = 0

        do j = 1, nchars
            if (ustr(j:j) .ne. ' ') then
                ifnobl = j
                go to 999
            end if
        end do

        999 continue
    end function ifnobl

    !> Left-justify a string.
    !!
    !! Leading blanks are removed, and the string is padded on the right with blanks.
    !!
    !! @private
    !!
    !! @param[in,out] ustr The string
    subroutine lejust(ustr)
        character(len=*), intent(inout) :: ustr

        integer j, jj, jbl, j1, nchars

        nchars = len(ustr)
        j1 = ifnobl(ustr)
        jbl = j1 - 1

        if (jbl .gt. 0) then
            do jj = j1, nchars
                j = jj - jbl
                ustr(j:j) = ustr(jj:jj)
            end do
            do j = nchars - jbl + 1, nchars
                ustr(j:j) = ' '
            end do
        end if
    end subroutine lejust

    !> Read the solid-solution superblock of a data1 file.
    !!
    !! Each solid solution becomes a new phase, of type `Solid`, whose component (end-member)
    !! species are created by cloning, with `clones`, the pure minerals of the same names. The
    !! activity coefficient model flag and parameters of each solid solution are also read. Reading
    !! stops at the `endit.` block.
    !!
    !! @private
    !!
    !! @param[out]    apxa      The interaction coefficients for the activity coefficients of each
    !!                          solid solution
    !! @param[in,out] axlksa    The polynomial coefficients for the log K of the reaction of each
    !!                          species
    !! @param[out]    bpxa      The site-mixing parameters for the activity coefficients of each
    !!                          solid solution
    !! @param[in,out] cdrsa     The reaction coefficients of all species
    !! @param[in,out] cessa     The elemental composition coefficients of all species
    !! @param[in]     iapxa_asv The maximum number of interaction coefficients for any solid
    !!                          solution
    !! @param[out]    iapxta    The number of interaction coefficients of each solid solution
    !! @param[in]     ibpxa_asv The maximum number of site-mixing parameters for any solid solution
    !! @param[out]    ibpxta    The number of site-mixing parameters of each solid solution
    !! @param[in]     ikta_asv  The maximum number of end-member component species in any solid
    !!                          solution
    !! @param[out]    jsola     The activity coefficient model flag of each solid solution
    !! @param[in,out] mwtspa    The molecular weights of the species
    !! @param[in]     nad1      The logical unit of the data1 file
    !! @param[in]     narx_asv  The maximum number of coefficients per temperature range
    !! @param[in,out] ncmpra    The indices of the first and last species of each phase
    !! @param[in,out] ndrsa     The species index of each reaction coefficient in `cdrsa`
    !! @param[in]     ndrsa_asv The size of `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsn     The number of entries used in `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsra    The indices of the first and last coefficients of the reaction of
    !!                          each species
    !! @param[in,out] nerr      The error count; incremented for a solid solution with no
    !!                          components, and for each component that is not a pure mineral
    !! @param[in,out] nessa     The element index of each composition coefficient in `cessa`
    !! @param[in]     nessa_asv The size of `cessa` and `nessa`
    !! @param[in,out] nessn     The number of entries used in `cessa` and `nessa`
    !! @param[in,out] nessra    The indices of the first and last coefficients of the composition of
    !!                          each species
    !! @param[in]     nmrn1a    The index of the first pure mineral
    !! @param[in]     nmrn2a    The index of the last pure mineral
    !! @param[in,out] np        The index of the last phase
    !! @param[in]     npta_asv  The maximum number of phases
    !! @param[in,out] ns        The index of the last species
    !! @param[in]     nsta_asv  The maximum number of species
    !! @param[in]     ntpr_asv  The maximum number of temperature ranges
    !! @param[in,out] nxta      The number of solid solutions
    !! @param[in]     nxta_asv  The maximum number of solid solutions
    !! @param[in,out] qclnsa    Whether each species was created by cloning
    !! @param[in]     uendit    The name marking the end of the superblock, `endit.`
    !! @param[in,out] uspeca    The names of the species, including their phase names
    !! @param[in,out] uphasa    The names of the phases
    !! @param[in]     uptsld    The type of solid phases, `Solid`
    !! @param[in,out] uptypa    The type of each phase
    !! @param[in,out] zchara    The electrical charges of the species
    subroutine indatp(apxa, axlksa, bpxa, cdrsa, cessa, iapxa_asv, iapxta, &
                      ibpxa_asv, ibpxta, ikta_asv, jsola, mwtspa, nad1, narx_asv, &
                      ncmpra, ndrsa, ndrsa_asv, ndrsn, ndrsra, nerr, nessa, &
                      nessa_asv, nessn, nessra, nmrn1a, nmrn2a, np, &
                      npta_asv, ns, nsta_asv, ntpr_asv, nxta, nxta_asv, &
                      qclnsa, uendit, uspeca, uphasa, uptsld, uptypa, zchara)
        integer iapxa_asv,ibpxa_asv,ikta_asv,narx_asv,ndrsa_asv,nessa_asv
        integer npta_asv,nsta_asv,ntpr_asv,nxta_asv
        integer iapxta(nxta_asv),ibpxta(nxta_asv),jsola(nxta_asv)
        integer ncmpra(2,npta_asv),ndrsa(ndrsa_asv),ndrsra(2,nsta_asv)
        integer nessa(nessa_asv),nessra(2,nsta_asv)
        integer nad1,ndrsn,nerr,nessn,nmrn1a,nmrn2a,np,ns,nxta
        logical qclnsa(nsta_asv)
        character(len=24) uphasa(npta_asv),uptypa(npta_asv)
        character(len=24) uptsld
        character(len=48) uspeca(nsta_asv)
        character(len=8) uendit
        real(kind=8) apxa(iapxa_asv,nxta_asv)
        real(kind=8) axlksa(narx_asv,ntpr_asv,nsta_asv)
        real(kind=8) bpxa(ibpxa_asv,nxta_asv),cdrsa(ndrsa_asv),cessa(nessa_asv)
        real(kind=8) mwtspa(nsta_asv),zchara(nsta_asv)
        integer jsolv,n,ncmptv,nsc,nx

        character(len=24) uphasv
        character(len=24), dimension(:), allocatable :: ucompv

        ALLOCATE(ucompv(ikta_asv))

        ! The label below defines a loop for reading the blocks in the superblock.
        100 continue

        ! Read a species block.
        read (nad1) uphasv,ncmptv,jsolv

        ! Check for end of this current superblock.
        if (uphasv(1:8) .eq. uendit(1:8)) go to 200
        np = np + 1
        uphasa(np) = uphasv
        uptypa(np) = uptsld

        nxta = nxta + 1
        nx = nxta
        jsola(nx) = jsolv

        if (ncmptv .gt. 0) then
            ! Read the names of component species.
            read (nad1) (ucompv(n), n = 1,ncmptv)
        else
            nerr = nerr + 1
        end if

        ! Read the activity coefficient parameters, first the ordinary parameters
        ! (apx), then the site-mixing parameters (bpx).
        read (nad1) iapxta(nx)
        if (iapxta(nx) .gt. 0) read (nad1) (apxa(n,nx), n = 1,iapxta(nx))
        read (nad1) ibpxta(nx)
        if (ibpxta(nx) .gt. 0) read (nad1) (bpxa(n,nx), n = 1,ibpxta(nx))

        ! Clone the component species.
        ncmpra(1,np) = ns + 1
        ncmpra(2,np) = ns + ncmptv
        do n = 1,ncmptv
            ns = ns + 1
            do nsc = nmrn1a,nmrn2a
                if (ucompv(n)(1:24) .eq. uspeca(nsc)(1:24)) then
                    call clones(axlksa, cdrsa, cessa, mwtspa, narx_asv, ndrsa, &
                                ndrsa_asv, ndrsn, ndrsra, nessa, nessa_asv, nessn, &
                                nessra, np, npta_asv, ns, nsc, nsta_asv, ntpr_asv, &
                                uphasa, uspeca, zchara)
                    qclnsa(ns) = .true.
                    go to 130
                end if
            end do

            ! The listed component was not found as a pure mineral species.
            nerr = nerr + 1
            130 continue
        end do

        ! Loop back to read another species block.
        go to 100

        200 DEALLOCATE(ucompv)
    end subroutine indatp

    !> Find a species by name within a range of species indices.
    !!
    !! Only the first 24 characters of each entry of `uspeca` (the species name, not the phase name)
    !! are compared.
    !!
    !! @private
    !!
    !! @param[in]  nrn1a  The index of the first species to search
    !! @param[in]  nrn2a  The index of the last species to search
    !! @param[out] ns     The index of the first matching species, or 0 if there is none
    !! @param[in]  nstmax The size of `uspeca`
    !! @param[in]  unam   The name of the species
    !! @param[in]  uspeca The names of the species
    subroutine srchn(nrn1a, nrn2a, ns, nstmax, unam, uspeca)
        integer nstmax
        integer nrn1a,nrn2a,ns
        character(len=48) uspeca(nstmax)
        character(len=24) unam

        do ns = nrn1a, nrn2a
            if (uspeca(ns)(1:24) .eq. unam(1:24)) go to 999
        end do

        ns = 0

        999 continue
    end subroutine srchn

    !> Read the Pitzer model parameters of the aqueous species.
    !!
    !! Two data block organizations are supported. In the classical organization (`jpdblo` = -1),
    !! the E-lambda flag is read from the data file, and each S-lambda(n) parameter of a pair has
    !! three coefficients (its 25C value and its first and second temperature derivatives). In the
    !! new organization, E-lambda terms are always used, and each parameter has `jpfc_asv`
    !! coefficients of the Pitzer parameter temperature function; only cation-anion pairs have
    !! S-lambda(1), ... parameters and alpha coefficients.
    !!
    !! The S-lambda pairs and the mu triplets are each read from two superblocks. Identical sets of
    !! alpha coefficients are stored once, in `palpaa`.
    !!
    !! @private
    !!
    !! @param[out]    amua      The coefficients of the temperature function of the mu parameter of
    !!                          each triplet
    !! @param[out]    aslma     The coefficients of the temperature functions of the S-lambda(0),
    !!                          S-lambda(1), ... parameters of each pair
    !! @param[out]    ielam     The E-lambda flag: -1 if E-lambda terms are not used, and 0 if they
    !!                          are
    !! @param[in]     ipbt_asv  The maximum number of alpha parameters for any species pair; must be
    !!                          2 for the classical organization
    !! @param[in]     jpdblo    The data block organization flag; -1 for the classical organization
    !! @param[in]     jpfc_asv  The number of coefficients in the parameter temperature function
    !! @param[in]     nad1      The logical unit of the data1 file
    !! @param[out]    nalpaa    The index in `palpaa` of the set of alpha coefficients of each pair
    !! @param[in]     napa_asv  The maximum number of distinct sets of alpha coefficients
    !! @param[out]    napta     The number of distinct sets of alpha coefficients
    !! @param[in]     narn1a    The index of the first aqueous species
    !! @param[in]     narn2a    The index of the last aqueous species
    !! @param[in,out] nerr      The error count; incremented if `ipbt_asv` is not 2 for the
    !!                          classical organization, or if the E-lambda flag is not recognized,
    !!                          in which case nothing more is read
    !! @param[out]    nmuta     The number of triplets for which mu coefficients are defined
    !! @param[in]     nmuta_asv The maximum number of triplets
    !! @param[out]    nmuxa     The species indices of each triplet (0 for a species that is not
    !!                          found)
    !! @param[out]    nslta     The number of pairs for which S-lambda coefficients are defined
    !! @param[in]     nslta_asv The maximum number of pairs
    !! @param[out]    nslxa     The species indices of each pair (0 for a species that is not found)
    !! @param[in]     nsta_asv  The maximum number of species
    !! @param[out]    palpaa    The distinct sets of alpha coefficients
    !! @param[in]     uspeca    The names of the species
    !! @param[in]     zchara    The electrical charges of the species, used to identify cation-anion
    !!                          pairs
    subroutine inupt(amua, aslma, ielam, ipbt_asv, jpdblo, jpfc_asv, nad1, &
                     nalpaa, napa_asv, napta, narn1a, narn2a, nerr, nmuta, &
                     nmuta_asv, nmuxa, nslta, nslta_asv, nslxa, nsta_asv, palpaa, &
                     uspeca, zchara)
        integer ipbt_asv,jpfc_asv,napa_asv,nmuta_asv,nslta_asv,nsta_asv

        integer nalpaa(nslta_asv),nmuxa(3,nmuta_asv),nslxa(2,nslta_asv)

        integer ielam,jpdblo,nad1,napta,narn1a,narn2a,nerr,nmuta,nslta

        character(len=48) uspeca(nsta_asv)

        real(8) amua(jpfc_asv,nmuta_asv)
        real(8) aslma(jpfc_asv,0:ipbt_asv,nslta_asv)
        real(8) palpaa(ipbt_asv,napa_asv)
        real(8) zchara(nsta_asv)

        integer i, j, ja, j2, nblock, nmu, ns, nsl

        logical qx

        character(len=80) uline
        character(len=24) unam1,unam2,unam3
        character(len=16) ux16
        character(len=8) uelam,uendit,ux8

        real(8) aax,z1,z2

        real(8), dimension(:), allocatable :: alphai

        data uendit /'endit.  '/

        ALLOCATE(alphai(ipbt_asv))

        if (jpdblo .eq. -1) then
            if (ipbt_asv .ne. 2) then
                write (ux8,'(i5)') ipbt_asv
                call lejust(ux8)
                j2 = ilnobl(ux8)
                nerr = nerr + 1
                go to 999
            end if
        end if

        if (jpdblo .eq. -1) then
            ! In the "classical" Pitzer data block organization, the E-lambda
            ! (E-theta) flag may be "on" or "off", as specified on the data
            ! file. Read and decode this flag.
            uelam = ' '
            read (nad1) uline
            uelam(1:8) = uline(17:24)
            if (uelam(1:3) .eq. 'off') then
                ielam = -1
            elseif (uelam(1:3) .eq. 'on ') then
                ielam = 0
            else
                j2 = ilnobl(uelam)
                nerr = nerr + 1
                go to 999
            end if
        else
            ! In the "new" Pitzer data block organization, the E-lambda flag is
            ! always "on".
            ielam = 0
        end if

        ! Read the species pairs for which S-lambda coefficients are defined.
        ! These data are comprised in two superblocks.
        ja = 0
        nsl = 0
        do nblock = 1,2
            ! Read a block.
            ! Read the names of the species in a pair.

            15   read (nad1) unam1,unam2

            ! Test for end of superblock.
            if (unam1(1:6) .eq. uendit(1:6)) go to 130

            ! Increment the S-lambda species pair counter.
            nsl = nsl + 1

            ! Calling sequence substitutions:
            !   narn1a for nrn1a
            !   narn2a for nrn2a
            !   unam1 for unam
            call srchn(narn1a,narn2a,ns,nsta_asv,unam1,uspeca)
            nslxa(1,nsl) = ns
            z1 = zchara(ns)

            ! Calling sequence substitutions:
            !   narn1a for nrn1a
            !   narn2a for nrn2a
            !   unam2 for unam
            call srchn(narn1a,narn2a,ns,nsta_asv,unam2,uspeca)
            nslxa(2,nsl) = ns
            z2 = zchara(ns)

            ! Read the temperature function coefficients for calculating
            ! Pitzer S-lambda(n) parameters. Read also the associated
            ! Pitzer alpha parameters.

            if (jpdblo .eq. -1) then
                ! Classical Pitzer data block organization.

                ! Read the lowest-order coefficients, which are here
                ! the 25C values of the corresponding interaction
                ! coefficients.
                read (nad1) (aslma(1,i,nsl), i = 0,2)

                ! Read the associated alpha coefficients.
                read (nad1) (alphai(i), i = 1,2)

                ! Read the higher-order coefficients, which here are
                ! first and second-order temperature derivatives.
                do i = 0,2
                    read (nad1) aslma(2,i,nsl),aslma(3,i,nsl)
                end do
            else
                ! New Pitzer data block organization.

                ! Read the associated alpha coefficients.
                if ((z1*z2) .lt. 0.) then
                    ! Read a larger set of data for cation-anion pairs.
                    do i = 1,ipbt_asv
                        read (nad1) ux16,alphai(i)
                    end do

                    do i = 0,ipbt_asv
                        read (nad1) ux16
                        do j = 1,jpfc_asv
                            read (nad1) aslma(j,i,nsl)
                        end do
                    end do
                else
                    ! Read a more limited set of data for all other pair types.
                    read (nad1) ux16
                    do j = 1,jpfc_asv
                        read (nad1) aslma(j,0,nsl)
                    end do
                end if
            end if

            ! Read the block terminator.
            read (nad1) uline(1:72)

            ! Test for alpha coefficient set already in the palpaa array.
            do j = 1,ja
                qx = .true.
                do i = 1,ipbt_asv
                    aax = abs(palpaa(i,j) - alphai(i))
                    if (aax .gt. 1.e-12) then
                        qx = .false.
                        go to 110
                    end if
                end do
                110     continue

                if (qx) then
                    ! Found the index to an existing alpha pair. Store this
                    ! index, then go process the data for another species pair.
                    nalpaa(nsl) = j
                    go to 15
                end if
            end do

            ! Not in the set; add it and store the index for this species pair.
            ja = ja + 1

            do i = 1,ipbt_asv
                palpaa(i,ja) = alphai(i)
            end do
            nalpaa(nsl) = ja

            ! Go process the data for another species pair.
            go to 15

            130   continue
        end do

        nslta = nsl
        napta = ja

        DEALLOCATE(alphai)

        ! Read the species triplets for which mu coefficients are
        ! defined. These data are comprised in two superblocks.

        nmu = 0
        do nblock = 1,2
            ! Read a block.

            ! Read the names of the species in a triplet.
            150   read (nad1) unam1,unam2,unam3

            ! Test for end of superblock.
            if (unam1(1:6) .eq. uendit(1:6)) go to 200


            ! Increment the mu species triplet counter.
            nmu = nmu + 1

            ! Calling sequence substitutions:
            !   narn1a for nrn1a
            !   narn2a for nrn2a
            !   unam1 for unam
            call srchn(narn1a,narn2a,ns,nsta_asv,unam1,uspeca)
            nmuxa(1,nmu) = ns

            ! Calling sequence substitutions:
            !   narn1a for nrn1a
            !   narn2a for nrn2a
            !   unam2 for unam
            call srchn(narn1a,narn2a,ns,nsta_asv,unam2,uspeca)
            nmuxa(2,nmu) = ns

            ! Calling sequence substitutions:
            !   narn1a for nrn1a
            !   narn2a for nrn2a
            !   unam3 for unam
            call srchn(narn1a,narn2a,ns,nsta_asv,unam3,uspeca)
            nmuxa(3,nmu) = ns

            ! Read the coefficients for calculating Pitzer mu parameters as a
            ! function of temperature.
            if (jpdblo .eq. -1) then

                ! Classical Pitzer data block organization.
                read (nad1) amua(1,nmu),amua(2,nmu),amua(3,nmu)
            else
                ! New Pitzer data block organization.
                read (nad1) ux16
                do j = 1,jpfc_asv
                    read (nad1) amua(j,nmu)
                enddo
            end if

            ! Read the block terminator.
            read (nad1) uline(1:72)

            go to 150

            200   continue
        end do

        nmuta = nmu
        999 continue
    end subroutine inupt

    !> Read the polynomial coefficients for a pressure derivative of a function, for each temperature range.
    !!
    !! @private
    !!
    !! @param[in]  data1    The logical unit of the data1 file
    !! @param[out] arr      The coefficients, of which those of order `ipc` are set
    !! @param[in]  ipc      The order of the pressure derivative
    !! @param[in]  ipcx_asv The maximum order of the pressure derivatives
    !! @param[in]  narxt    The number of coefficients in each temperature range
    !! @param[in]  narx_asv The maximum number of coefficients per temperature range
    !! @param[in]  ntprt    The number of temperature ranges
    !! @param[in]  ntpr_asv The maximum number of temperature ranges
    !! @param[out] ux24     The label preceding the coefficients
    subroutine indatd(data1, arr, ipc, ipcx_asv, narxt, narx_asv, ntprt, ntpr_asv, ux24)
        integer ipcx_asv,narx_asv,ntpr_asv

        integer data1
        integer narxt(ntpr_asv)
        integer ipc, ntprt
        real(kind=8) arr(narx_asv,ntpr_asv,ipcx_asv)
        character(len=24) ux24

        integer n, ntpr

        read (data1) ux24
        do ntpr = 1, ntprt
            read (data1) (arr(n,ntpr,ipc), n = 1,narxt(ntpr))
        end do
    end subroutine indatd

    !> Read a superblock of species blocks from a data1 file.
    !!
    !! Each block gives a species' name, molecular weight, charge and elemental composition and,
    !! unless it is a basis species, its reaction and the polynomial coefficients for its log K.
    !! These are followed by the coefficients of its enthalpy and volume functions and their
    !! pressure derivatives, if they are represented (`ipch` and `ipcv` are non-negative). Molar
    !! volumes are not read. Reading stops at the `endit.` block.
    !!
    !! The kind of superblock is given by `usblkf`. Pure minerals (and pure liquids) are phases of
    !! their own, while other species belong to the phase `uphasv`.
    !!
    !! A species with no reaction is a basis species, and is given a reaction with a single null
    !! species. Otherwise, the species is moved to the start of its reaction, and the other species
    !! in the reaction are added to the basis set (`ubasp`) if they are not already in it. Their
    !! basis indices are stored in `ndrsa`, to be converted to species indices by `dfbasp`, which
    !! allows a reaction to refer to a basis species that has not yet been read. A species with no
    !! elements is given a single null element.
    !!
    !! @private
    !!
    !! @param[in,out] adhfsa    The polynomial coefficients for the pressure derivatives of the
    !!                          enthalpy function of each species
    !! @param[in,out] advfsa    The polynomial coefficients for the pressure derivatives of the
    !!                          volume function of each species
    !! @param[in,out] axhfsa    The polynomial coefficients for the enthalpy function of each
    !!                          species
    !! @param[in,out] axlksa    The polynomial coefficients for the log K of the reaction of each
    !!                          species
    !! @param[in,out] axvfsa    The polynomial coefficients for the volume function of each species
    !! @param[in,out] cdrsa     The reaction coefficients of all species
    !! @param[out]    cdrsv     Workspace for the reaction coefficients of a species
    !! @param[in,out] cessa     The elemental composition coefficients of all species
    !! @param[out]    cessv     Workspace for the composition coefficients of a species
    !! @param[in]     ipch      The order of the pressure corrections to enthalpy functions;
    !!                          negative if they are not represented
    !! @param[in]     ipch_asv  The maximum order of the pressure corrections to enthalpy functions
    !! @param[in]     ipcv      The order of the pressure corrections to volume functions; negative
    !!                          if they are not represented
    !! @param[in]     ipcv_asv  The maximum order of the pressure corrections to volume functions
    !! @param[in,out] mwtspa    The molecular weights of the species
    !! @param[in]     nad1      The logical unit of the data1 file
    !! @param[in]     narxt     The number of coefficients in each temperature range
    !! @param[in]     narx_asv  The maximum number of coefficients per temperature range
    !! @param[in,out] nata      The number of aqueous species
    !! @param[in,out] nbta      The number of basis species
    !! @param[in]     nbta_asv  The maximum number of basis species
    !! @param[in]     nbta1_asv The maximum number of species in a reaction
    !! @param[in]     nbtafd    The number of leading species on the data file that are basis
    !!                          species
    !! @param[in,out] ncmpra    The indices of the first and last species of each phase
    !! @param[in]     ncta      The number of chemical elements
    !! @param[in]     ncta_asv  The maximum number of chemical elements
    !! @param[in,out] ndrsa     The species (or, temporarily, basis) index of each reaction
    !!                          coefficient in `cdrsa`
    !! @param[in]     ndrsa_asv The size of `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsn     The number of entries used in `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsra    The indices of the first and last coefficients of the reaction of
    !!                          each species
    !! @param[in,out] nerr      The error count; incremented for an unrecognized element, for a
    !!                          species with no elements other than e- or O2(g) outside the gas
    !!                          superblock, for a reaction with only one species, for a species
    !!                          missing from its own reaction, and for each unexpected label
    !! @param[in,out] nessa     The element index of each composition coefficient in `cessa`
    !! @param[in]     nessa_asv The size of `cessa` and `nessa`
    !! @param[in,out] nessn     The number of entries used in `cessa` and `nessa`
    !! @param[in,out] nessra    The indices of the first and last coefficients of the composition of
    !!                          each species
    !! @param[in,out] ngta      The number of gas species
    !! @param[in,out] nlta      The number of pure liquids
    !! @param[in,out] nmta      The number of pure minerals
    !! @param[in,out] np        The index of the last phase
    !! @param[in]     npta_asv  The maximum number of phases
    !! @param[in,out] ns        The index of the last species
    !! @param[in]     nsta_asv  The maximum number of species
    !! @param[in]     ntprt     The number of temperature ranges
    !! @param[in]     ntpr_asv  The maximum number of temperature ranges
    !! @param[in]     uaqsln    The name and type of the aqueous phase, `Aqueous solution`
    !! @param[in,out] ubasp     The names of the basis species
    !! @param[out]    udrsv     Workspace for the names of the species in a reaction
    !! @param[in]     uelema    The names of the chemical elements
    !! @param[in]     uendit    The name marking the end of the superblock, `endit.`
    !! @param[out]    uessv     Workspace for the names of the elements of a species
    !! @param[in,out] uphasa    The names of the phases
    !! @param[in,out] uphasv    The name of the phase of the species; set to the species name for
    !!                          pure minerals and liquids
    !! @param[in]     uptgas    The type of gas phases, `Gas`
    !! @param[in]     uptliq    The type of liquid phases, `Liquid`
    !! @param[in]     uptsld    The type of solid phases, `Solid`
    !! @param[in,out] uptypa    The type of each phase
    !! @param[in]     usblkf    The kind of superblock: `Aqueous solution`, `Solid`, `Liquid` or
    !!                          `Gas`
    !! @param[in,out] uspeca    The names of the species, including their phase names
    !! @param[in,out] vosp0a    The molar volumes of the species, which are set to zero
    !! @param[in,out] zchara    The electrical charges of the species
    subroutine indats(adhfsa, advfsa, axhfsa, axlksa, axvfsa, cdrsa, cdrsv, cessa, &
                      cessv, ipch, ipch_asv, ipcv, ipcv_asv, mwtspa, nad1, narxt, &
                      narx_asv, nata, nbta, nbta_asv, nbta1_asv, nbtafd, &
                      ncmpra, ncta, ncta_asv, ndrsa, ndrsa_asv, ndrsn, ndrsra, &
                      nerr, nessa, nessa_asv, nessn, nessra, ngta, nlta, &
                      nmta, np, npta_asv, ns, nsta_asv, ntprt, &
                      ntpr_asv, uaqsln, ubasp, udrsv, uelema, uendit, uessv, &
                      uphasa, uphasv, uptgas, uptliq, uptsld, uptypa, usblkf, &
                      uspeca, vosp0a, zchara)

        integer ipch_asv,ipcv_asv,narx_asv,nbta_asv,nbta1_asv
        integer ncta_asv,ndrsa_asv,nessa_asv,npta_asv
        integer nsta_asv,ntpr_asv

        integer narxt(ntpr_asv),ncmpra(2,npta_asv),ndrsa(ndrsa_asv)
        integer ndrsra(2,nsta_asv),nessa(nessa_asv),nessra(2,nsta_asv)

        integer ipch,ipcv,nad1,nata,nbta,nbtafd,ncta,ndrsn,nerr
        integer nessn,ngta,nlta,nmta,np,ns,ntprt

        character(len=48) ubasp(nbta_asv),uspeca(nsta_asv)
        character(len=24) udrsv(nbta1_asv),uphasa(npta_asv),uptypa(npta_asv)
        character(len=24) uphasv,uaqsln,uptsld,uptliq,uptgas,usblkf
        character(len=8) uelema(ncta_asv),uessv(ncta_asv)
        character(len=8) uendit

        real(kind=8) adhfsa(narx_asv,ntpr_asv,ipch_asv,nsta_asv)
        real(kind=8) advfsa(narx_asv,ntpr_asv,ipcv_asv,nsta_asv)
        real(kind=8) axhfsa(narx_asv,ntpr_asv,nsta_asv)
        real(kind=8) axlksa(narx_asv,ntpr_asv,nsta_asv)
        real(kind=8) axvfsa(narx_asv,ntpr_asv,nsta_asv),cdrsa(ndrsa_asv)
        real(kind=8) cdrsv(nbta1_asv),cessa(nessa_asv),cessv(ncta_asv)
        real(kind=8) mwtspa(nsta_asv),vosp0a(nsta_asv),zchara(nsta_asv)

        integer ipc,j2,j3,j4,j5,j6,j7,n,nb,nc,nctsv,ndrstv,nf,ntpr

        character(len=24) uelect,uhx,uspecv,ux24

        data uelect /'e-                      '/

        100 continue

        ! Read a species block.
        !   uspecv = species name
        !   nctsv  = number of chemical elements comprising the species
        !   ndrstv = number of reaction coefficients in the reaction
        !          associated with the species
        read (nad1) uspecv,nctsv,ndrstv
        j2 = ilnobl(uspecv)
        j5 = ilnobl(usblkf)

        ! Check for the end of the current superblock.
        if (uspecv(1:8) .eq. uendit(1:8)) go to 999

        ! If the species is a pure mineral or pure liquid, set the phase name to
        ! match the species name.
        if (usblkf(1:24).eq.uptsld(1:24) .or. usblkf(1:24).eq.uptliq(1:24)) then
            uphasv(1:24) = uspecv(1:24)
        end if
        j3 = ilnobl(uphasv)

        ! Have another species.
        ns = ns + 1

        ! Load the species name array. Note that the last 24 characters contain the
        ! name of the associated phase.
        uspeca(ns)(1:24) = uspecv(1:24)
        uspeca(ns)(25:48) = uphasv(1:24)

        ! mwtspa = molecular weight
        ! zchara = electrical charge
        ! vosp0a = molar volume (not read).
        read (nad1) mwtspa(ns),zchara(ns)
        vosp0a(ns) = 0.

        ! cessv  = chemical element stoichiometric coefficient
        ! uessv  = name of corresponding chemical element.
        if (nctsv .gt. 0) read (nad1) (cessv(n),uessv(n), n = 1,nctsv)

        ! Decode the elemental composition.
        nessra(1,ns) = nessn + 1
        if (nctsv .gt. 0) then
            do n = 1,nctsv
                do nc = 1,ncta
                    if (uessv(n)(1:8) .eq. uelema(nc)(1:8)) then
                        nessn = nessn + 1
                        cessa(nessn) = cessv(n)
                        nessa(nessn) = nc
                        go to 120
                    end if
                end do
                j4 = ilnobl(uessv(n))
                nerr = nerr + 1
                120  continue
            end do
            nessra(2,ns) = nessn
        else
            ! Have a species comprised of no chemical elements. This is permitted
            ! only for the following:
            !   O2(g) in a phase other than "gas"
            !   e-    in any phase
            if (uspecv(1:5) .eq. 'O2(g)') then
                if (usblkf(1:24) .eq. uptgas(1:24)) then
                    nerr = nerr + 1
                end if
            else if (uspecv(1:2) .ne. uelect(1:2)) then
                nerr = nerr + 1
            end if

            ! A species with no elements is treated as being comprised of one "null"
            ! element.
            nessn = nessn + 1
            cessa(nessn) = 0.
            nessa(nessn) = 0
            nessra(2,ns) = nessn
        end if

        ! Read the associated reaction data, if any.

        ! Read the reaction, if any.
        if (ndrstv .gt. 0) then
            read (nad1) (cdrsv(n),udrsv(n), n = 1,ndrstv)
        endif

        ! Decode the associated reaction into a temporary format. The species
        ! associated with the reaction is moved if necessary so that it is the first
        ! species to appear in the reaction. Its species index is stored in the
        ! ndrsa array. The other species are presumed to be basis species. If one
        ! of these species has not been already loaded into the ubasp array, it is
        ! loaded at this time. The basis number of the species is stored in the
        ! ndrsa array. It will be converted to the corresponding species number
        ! after all species are loaded. This scheme permits the loading of a
        ! reaction which is written in terms of a basis species which itself has not
        ! yet been loaded.
        ndrsra(1,ns) = ndrsn + 1
        if (ndrstv .le. 0) then
            ! A species with no reaction listed on the data file is treated as a
            ! basis species. An associated reaction with one "null" species is
            ! created. The actual reaction is formally treated as one in which one
            ! mole of the associated species is destroyed and one mole of the same
            ! species is created. This is termed an "identity reaction." However,
            ! the reaction stored is not the identity reaction but the one with the
            ! "null" species as the only species.
            nbta = nbta + 1
            ubasp(nbta) = uspeca(ns)
            ndrsn = ndrsn + 1
            cdrsa(ndrsn) = 0.
            ndrsa(ndrsn) = 0
            ndrsra(2,ns) = ndrsn
            do ntpr = 1,ntpr_asv
                do n = 1,narx_asv
                    axlksa(n,ntpr,ns) = 0.
                end do
            end do
        else if (ndrstv .eq. 1) then
            nerr = nerr + 1
        else
            ! Make sure that the species associated with the reaction is the first
            ! species in the reaction.
            do n = 1,ndrstv
                if (udrsv(n)(1:24) .eq. uspecv(1:24)) then
                    ndrsn = ndrsn + 1
                    cdrsa(ndrsn) = cdrsv(n)
                    ndrsa(ndrsn) = ns
                    go to 160
                end if
            end do

            udrsv(1) = uspecv
            nerr = nerr + 1

            160   nf = 0

            do n = 1,ndrstv
                if (udrsv(n)(1:24).eq.uspecv(1:24) .and. nf.eq.0) then
                    nf = 1
                    if (ns .le. nbtafd) then
                        ! The species is in the range of aqueous species that are
                        ! intended to be basis species. Add it to the basis set.
                        nbta = nbta + 1
                        ubasp(nbta) = udrsv(n)
                    end if
                else
                    ndrsn = ndrsn + 1
                    cdrsa(ndrsn) = cdrsv(n)
                    do nb = 1,nbta
                        if (ubasp(nb)(1:24) .eq. udrsv(n)(1:24)) then
                            ndrsa(ndrsn) = nb
                            go to 180
                        end if
                    end do

                    ! The reaction is written in terms of another species that is
                    ! not yet in the basis set. Add it to that set.
                    nbta = nbta + 1
                    ubasp(nbta) = udrsv(n)
                    ndrsa(ndrsn) = nbta
                end if
                180  continue
            end do

            ndrsra(2,ns) = ndrsn

            ! Read the interpolating polynomial coefficients for the log K of the
            ! reaction.
            read (nad1) ux24
            j6 = ilnobl(ux24)
            uhx = 'Log K'
            j7 = ilnobl(uhx)
            if (uhx(1:j7) .ne. ux24(1:j6)) then
                nerr = nerr + 1
            end if
            do ntpr = 1,ntprt
                read (nad1) (axlksa(n,ntpr,ns), n = 1,narxt(ntpr))
            end do
        end if

        if (ipch .ge. 0) then
            ! Read the interpolating polynomial coefficients for the enthalpy
            ! function and its pressure derivatives. For a basis species, the
            ! enthalpy function is the standard partial molar enthalpy of formation;
            ! for all other species, the enthalpy function is the standard partial
            ! molar enthalpy of reaction.
            read (nad1) ux24
            j6 = ilnobl(ux24)
            uhx = 'Enthalpy'
            j7 = ilnobl(uhx)
            if (uhx(1:j7) .ne. ux24(1:j6)) then
                nerr = nerr + 1
            end if
            do ntpr = 1,ntprt
                read (nad1) (axhfsa(n,ntpr,ns), n = 1,narxt(ntpr))
            end do
            do ipc = 1,ipch
                read (nad1) ux24
                j6 = ilnobl(ux24)
                if (ipc .eq. 1) then
                    uhx = 'dEnthalpy/dP'
                else
                    uhx = 'd( )Enthalpy/dP( )'
                    write (uhx(3:3),'(i1)') ipc
                    write (uhx(17:17),'(i1)') ipc
                end if
                j7 = ilnobl(uhx)
                if (uhx(1:j7) .ne. ux24(1:j6)) then
                    nerr = nerr + 1
                end if
                do ntpr = 1,ntprt
                    read (nad1) (adhfsa(n,ntpr,ipc,ns), n = 1,narxt(ntpr))
                end do
            end do
        end if

        if (ipcv .ge. 0) then
            ! Read the interpolating polynomial coefficients for the volume function
            ! and its pressure derivatives. For a basis species, the volume function
            ! is the standard partial molar enthalpy of formation; for all other
            ! species, the volume function is the standard partial molar volume
            ! of reaction.
            read (nad1) ux24
            j6 = ilnobl(ux24)
            uhx = 'Volume'
            j7 = ilnobl(uhx)
            if (uhx(1:j7) .ne. ux24(1:j6)) then
                nerr = nerr + 1
            end if
            do ntpr = 1,ntprt
                read (nad1) (axvfsa(n,ntpr,ns), n = 1,narxt(ntpr))
            end do
            do ipc = 1,ipcv
                read (nad1) ux24
                j6 = ilnobl(ux24)
                if (ipc .eq. 1) then
                    uhx = 'dVolume/dP'
                else
                    uhx = 'd( )Volume/dP( )'
                    write (uhx(3:3),'(i1)') ipc,ipc
                    write (uhx(15:15),'(i1)') ipc,ipc
                end if
                j7 = ilnobl(uhx)
                if (uhx(1:j7) .ne. ux24(1:j6)) then
                    nerr = nerr + 1
                end if
                do ntpr = 1,ntprt
                    read (nad1) (advfsa(n,ntpr,ipc,ns), n = 1,narxt(ntpr))
                end do
            end do
        end if

        if (usblkf(1:24) .eq. uaqsln(1:24)) nata = nata + 1

        if (usblkf(1:24) .eq. uptsld(1:24)) then
            nmta = nmta + 1
            np = np + 1
            uphasa(np) = uspecv
            uptypa(np) = uptsld
            ncmpra(1,np) = ns
            ncmpra(2,np) = ns
        end if

        if (usblkf(1:24) .eq. uptliq(1:24)) then
            nlta = nlta + 1
            np = np + 1
            uphasa(np) = uspecv
            uptypa(np) = uptliq
            ncmpra(1,np) = ns
            ncmpra(2,np) = ns
        end if

        if (usblkf(1:24) .eq. uptgas(1:24)) ngta = ngta + 1

        ! Loop back to read another species block.
        go to 100

        999 continue
    end subroutine indats

    !> Read the polynomial coefficients of a function, for each temperature range.
    !!
    !! @private
    !!
    !! @param[in]  data1    The logical unit of the data1 file
    !! @param[out] arr      The coefficients
    !! @param[in]  narx_asv The maximum number of coefficients per temperature range
    !! @param[in]  narxt    The number of coefficients in each temperature range
    !! @param[in]  ntpr_asv The maximum number of temperature ranges
    !! @param[in]  ntprt    The number of temperature ranges
    !! @param[out] ux24     The label preceding the coefficients
    subroutine indatc(data1, arr, narx_asv, narxt, ntpr_asv, ntprt, ux24)
        integer, intent(in) :: data1

        integer narx_asv, ntpr_asv
        integer narxt(ntpr_asv)
        integer ntprt
        real(kind=8) arr(narx_asv,ntpr_asv)
        character(len=24) ux24
        integer n, ntpr

        read (data1) ux24
        do ntpr = 1,ntprt
            read (data1) (arr(n,ntpr), n = 1,narxt(ntpr))
        enddo
    end subroutine indatc

    !> Clone a species as a species of another phase.
    !!
    !! The `nsc`-th species is copied into the `ns`-th, which belongs to the `np`-th phase.
    !! Typically, the `nsc`-th species is a pure mineral or liquid, and the `ns`-th species is the
    !! corresponding component species of a solid or liquid solution. The name (with the new phase
    !! name), molecular weight, charge, elemental composition, reaction and log K coefficients are
    !! copied. If the `nsc`-th species is a basis species, with only an identity reaction, the clone
    !! is instead given a reaction linking it to the `nsc`-th species.
    !!
    !! @private
    !!
    !! @param[in,out] axlksa    The polynomial coefficients for the log K of the reaction of each
    !!                          species
    !! @param[in,out] cdrsa     The reaction coefficients of all species
    !! @param[in,out] cessa     The elemental composition coefficients of all species
    !! @param[in,out] mwtspa    The molecular weights of the species
    !! @param[in]     narx_asv  The maximum number of coefficients per temperature range
    !! @param[in,out] ndrsa     The species index of each reaction coefficient in `cdrsa`
    !! @param[in]     ndrsa_asv The size of `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsn     The number of entries used in `cdrsa` and `ndrsa`
    !! @param[in,out] ndrsra    The indices of the first and last coefficients of the reaction of
    !!                          each species
    !! @param[in,out] nessa     The element index of each composition coefficient in `cessa`
    !! @param[in]     nessa_asv The size of `cessa` and `nessa`
    !! @param[in,out] nessn     The number of entries used in `cessa` and `nessa`
    !! @param[in,out] nessra    The indices of the first and last coefficients of the composition of
    !!                          each species
    !! @param[in]     np        The index of the phase of the clone
    !! @param[in]     npta_asv  The maximum number of phases
    !! @param[in]     ns        The index of the clone
    !! @param[in]     nsc       The index of the species to clone
    !! @param[in]     nsta_asv  The maximum number of species
    !! @param[in]     ntpr_asv  The maximum number of temperature ranges
    !! @param[in]     uphasa    The names of the phases
    !! @param[in,out] uspeca    The names of the species, including their phase names
    !! @param[in,out] zchara    The electrical charges of the species
    subroutine clones(axlksa, cdrsa, cessa, mwtspa, narx_asv, ndrsa, ndrsa_asv, &
                      ndrsn, ndrsra, nessa, nessa_asv, nessn, nessra, np, &
                      npta_asv, ns, nsc, nsta_asv, ntpr_asv, uphasa, uspeca, zchara)
        integer narx_asv,ndrsa_asv,nessa_asv,npta_asv,nsta_asv,ntpr_asv

        integer ndrsa(ndrsa_asv)
        integer ndrsra(2,nsta_asv)
        integer nessa(nessa_asv)
        integer nessra(2,nsta_asv)

        integer ndrsn,nessn,np,ns,nsc

        character(len=24) uphasa(npta_asv)
        character(len=48) uspeca(nsta_asv)

        real(kind=8) axlksa(narx_asv,ntpr_asv,nsta_asv),cessa(nessa_asv)
        real(kind=8) cdrsa(ndrsa_asv),mwtspa(nsta_asv),zchara(nsta_asv)

        integer i,j,ndrsn1,nessn1,nr1,nr2,nse,nt

        ! Copy the name, molecular weight, and electrical charge.
        ! Note that the phase part of the name is different.
        uspeca(ns)(1:24) = uspeca(nsc)(1:24)
        uspeca(ns)(25:48) = uphasa(np)(1:24)
        mwtspa(ns) = mwtspa(nsc)
        zchara(ns) = zchara(nsc)

        ! Copy the elemental composition.
        nessra(1,ns) = nessn + 1
        nr1 = nessra(1,nsc)
        nr2 = nessra(2,nsc)
        do nessn1 = nr1,nr2
            nessn = nessn + 1
            cessa(nessn) = cessa(nessn1)
            nessa(nessn) = nessa(nessn1)
        end do
        nessra(2,ns) = nessn

        ! Copy the associated reaction.
        ndrsra(1,ns) = ndrsn + 1
        nr1 = ndrsra(1,nsc)
        nr2 = ndrsra(2,nsc)
        nt = nr2 - nr1 + 1
        if (nt .lt. 2) then
            ! The nsc-th species is a data file basis species that has only an
            ! identity reaction. Write a linking reaction.
            ndrsn = ndrsn + 1
            cdrsa(ndrsn) = -1.
            ndrsa(ndrsn) = ns
            ndrsn = ndrsn + 1
            cdrsa(ndrsn) = 1.
            ndrsa(ndrsn) = nsc
        else
            ! The nsc-th species has a reaction which can be copied.
            do ndrsn1 = nr1,nr2
                ndrsn = ndrsn + 1
                cdrsa(ndrsn) = cdrsa(ndrsn1)
                nse = ndrsa(ndrsn1)
                if (nse .eq. nsc) nse = ns
                ndrsa(ndrsn) = nse
            end do
        end if
        ndrsra(2,ns) = ndrsn

        ! Copy the coefficients of the polynomials which represent the thermodynamic
        ! functions of the reaction. Note that this is valid whether the reaction
        ! is an identity reaction or a real one.
        do j = 1,ntpr_asv
            do i = 1,narx_asv
              axlksa(i,j,ns) = axlksa(i,j,nsc)
            end do
        end do
    end subroutine clones

    !> Resolve the basis species collected while reading the species.
    !!
    !! The species index of each basis species in `ubasp` is stored in `nbaspa`, and its name is
    !! expanded to the full 48 characters (including the phase name). The basis indices stored in
    !! `ndrsa` by `indats` are then replaced by the corresponding species indices. A basis species
    !! that is not found is given the index 0.
    !!
    !! @private
    !!
    !! @param[out]    nbaspa    The species index of each basis species
    !! @param[in]     nbta      The number of basis species
    !! @param[in]     nbta_asv  The maximum number of basis species
    !! @param[in,out] ndrsa     The index of each reaction coefficient's species; basis indices on
    !!                          input, species indices on output
    !! @param[in]     ndrsa_asv The size of `ndrsa`
    !! @param[in]     ndrsra    The indices of the first and last coefficients of the reaction of
    !!                          each species
    !! @param[in,out] nerr      The error count; incremented for each basis species that is not
    !!                          found
    !! @param[in]     nsta      The number of species
    !! @param[in]     nsta_asv  The maximum number of species
    !! @param[in,out] ubasp     The names of the basis species
    !! @param[in]     uspeca    The names of the species
    subroutine dfbasp(nbaspa, nbta, nbta_asv, ndrsa, ndrsa_asv, ndrsra, nerr, &
                      nsta, nsta_asv, ubasp, uspeca)
        integer nbta_asv, ndrsa_asv, nsta_asv
        integer nbaspa(nbta_asv),ndrsa(ndrsa_asv),ndrsra(2,nsta_asv)
        integer nbta,nerr,nsta
        character(len=48) ubasp(nbta_asv),uspeca(nsta_asv)
        integer jlen,n,nb,ns,nr1,nr1p1,nr2,nt
        character(len=56) uspn56
        ! Set up the nbaspa array and expand the elements of the ubasp array to the
        ! full 48 characters.
        do nb = 1,nbta
            do ns = 1,nsta
                if (uspeca(ns)(1:24) .eq. ubasp(nb)(1:24)) then
                    nbaspa(nb) = ns
                    ubasp(nb)(1:48) = uspeca(ns)(1:48)
                    go to 105
              end if
            end do

            nbaspa(nb) = 0

            ! Calling sequence substitutions:
            !     ubasp(nb) for unam48

            call fmspnm(jlen,ubasp(nb),uspn56)
            nerr = nerr + 1
      105   continue
        end do
        ! Convert basis species indices in the ndrsa array to species indices.
        do ns = 1,nsta
            nt = ndrsra(2,ns) - ndrsra(1,ns) + 1
            if (nt .ge. 2) then
                nr1 = ndrsra(1,ns)
                nr1p1 = nr1 + 1
                nr2 = ndrsra(2,ns)
                do n = nr1p1,nr2
                    nb = ndrsa(n)
                    ndrsa(n) = nbaspa(nb)
              end do
          end if
        end do
    end subroutine dfbasp

    !> Format a 48-character species name for messages.
    !!
    !! The phase part of the name (the second 24 characters) is placed in parentheses after the
    !! species part (the first 24 characters). For example, ignoring trailing blanks, `"Albite
    !! Plagioclase"` is formatted as `"Albite (Plagioclase)"`. The phase part is omitted if it is
    !! blank or identical to the species part, so pure Albite is formatted as `"Albite"`, not
    !! `"Albite (Albite)"`.
    !!
    !! This is similar to the EQLIB routine `fmspnx`, which also omits the phase part if the phase
    !! is `Aqueous solution`.
    !!
    !! @private
    !!
    !! @param[out] jlen   The length of the formatted name, excluding trailing blanks
    !! @param[in]  unam48 The 48-character species name
    !! @param[out] uspn56 The formatted name
    subroutine fmspnm(jlen, unam48, uspn56)
        integer jlen

        character(len=48) unam48
        character(len=56) uspn56

        integer j2

        character(len=24) uphnam

        uspn56 = unam48(1:24)
        jlen = ilnobl(uspn56)

        uphnam = unam48(25:48)
        j2 = ilnobl(uphnam)
        if (uphnam(1:24) .ne. unam48(1:24)) then
            if (j2 .gt. 0) then
                uspn56(jlen + 1:jlen + 2) = ' ('
                uspn56(jlen + 3:jlen + 2 + j2) = uphnam(1:j2)
                jlen = jlen + 3 + j2
                uspn56(jlen:jlen) = ')'
            end if
         end if
    end subroutine fmspnm
end module pyeq36_data1
