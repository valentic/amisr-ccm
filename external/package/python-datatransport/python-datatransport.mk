################################################################################
#
# python-datatransport
#
################################################################################

PYTHON_DATATRANSPORT_VERSION = 3.0.9
PYTHON_DATATRANSPORT_SOURCE = datatransport-$(PYTHON_DATATRANSPORT_VERSION).tar.gz
PYTHON_DATATRANSPORT_SITE = https://files.pythonhosted.org/packages/58/92/1e8650dd1f1a73227bd554080797a58b47070ebed78ee9279523a3f03499
PYTHON_DATATRANSPORT_SETUP_TYPE = setuptools
PYTHON_DATATRANSPORT_LICENSE = GNU General Public License v3 (GPLv3)
PYTHON_DATATRANSPORT_LICENSE_FILES = LICENSE

$(eval $(python-package))
