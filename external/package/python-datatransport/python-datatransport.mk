################################################################################
#
# python-datatransport
#
################################################################################

PYTHON_DATATRANSPORT_VERSION = 3.0.17
PYTHON_DATATRANSPORT_SOURCE = datatransport-$(PYTHON_DATATRANSPORT_VERSION).tar.gz
PYTHON_DATATRANSPORT_SITE = https://files.pythonhosted.org/packages/29/a3/d69669a780197410f13d8c8697502b9c1503408e063ce84c4ed731c948f2
PYTHON_DATATRANSPORT_SETUP_TYPE = setuptools
PYTHON_DATATRANSPORT_LICENSE = GNU General Public License v3 (GPLv3)
PYTHON_DATATRANSPORT_LICENSE_FILES = LICENSE

$(eval $(python-package))
