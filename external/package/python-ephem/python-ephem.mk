################################################################################
#
# python-ephem
#
################################################################################

PYTHON_EPHEM_VERSION = 4.1.4
PYTHON_EPHEM_SOURCE = ephem-$(PYTHON_EPHEM_VERSION).tar.gz
PYTHON_EPHEM_SITE = https://files.pythonhosted.org/packages/af/5d/bbd70a7538f6d6138583a59a73e8ee85a8b838ac5a284e1dedb2127a9369
PYTHON_EPHEM_SETUP_TYPE = distutils
PYTHON_EPHEM_LICENSE = MIT
PYTHON_EPHEM_LICENSE_FILES = LICENSE

$(eval $(python-package))
