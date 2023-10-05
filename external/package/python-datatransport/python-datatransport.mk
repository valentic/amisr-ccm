################################################################################
#
# python-datatransport
#
################################################################################

PYTHON_DATATRANSPORT_VERSION = 3.0.18
PYTHON_DATATRANSPORT_SOURCE = datatransport-$(PYTHON_DATATRANSPORT_VERSION).tar.gz
PYTHON_DATATRANSPORT_SITE = https://files.pythonhosted.org/packages/4c/e0/17db1b4141aff02c4cfeaf6a231bdac02ab573ec7d9875b77a0bebe90ad5
PYTHON_DATATRANSPORT_SETUP_TYPE = setuptools
PYTHON_DATATRANSPORT_LICENSE = GNU General Public License v3 (GPLv3)
PYTHON_DATATRANSPORT_LICENSE_FILES = LICENSE

$(eval $(python-package))
