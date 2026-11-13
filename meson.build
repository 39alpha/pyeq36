project(
  'pyeq36',
  'fortran',
  version: '0.1.0',
  meson_version: '>= 0.60',
  default_options: [
    'fortran_std=f2008',
    'buildtype=debugoptimized',
    'warning_level=everything',
  ]
)

fc = meson.get_compiler('fortran')

add_project_arguments(
  fc.get_supported_arguments('-ffp-contract=off', '-Wno-compare-reals', '-fmax-errors=0', '-ffree-line-length-3000'),
  language: 'fortran',
)

if get_option('buildtype') in ['debug', 'debugoptimized']
  add_project_arguments(
    fc.get_supported_arguments('-ffpe-trap=invalid', '-finit-real=snan', '-finit-logical=false', '-finit-derived', '-finit-integer=-2147483647', '-fcheck=all', '-fbacktrace', '-fcoarray=single'),
    language: 'fortran',
  )
endif

if get_option('buildtype') == 'release'
  release_args = fc.get_supported_arguments('-flto=auto', '-funroll-loops')
  add_project_arguments(release_args, language: 'fortran')
  add_project_link_arguments(fc.get_supported_arguments('-flto=auto'), language: 'fortran')
endif

link_args = host_machine.system() == 'windows' ? ['-static'] : []

shared_library('pyeq36', 'src/eq36/pyeq36_data1.f90', link_args: link_args)
