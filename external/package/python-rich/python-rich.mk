################################################################################
#
# python-rich
#
################################################################################

PYTHON_RICH_VERSION = 13.4.2
PYTHON_RICH_SOURCE = rich-$(PYTHON_RICH_VERSION).tar.gz
PYTHON_RICH_SITE = https://files.pythonhosted.org/packages/e3/12/67d0098eb77005f5e068de639e6f4cfb8f24e6fcb0fd2037df0e1d538fee
PYTHON_RICH_SETUP_TYPE = pep517 
PYTHON_RICH_LICENSE = MIT
PYTHON_RICH_LICENSE_FILES = LICENSE
PYTHON_RICH_DEPENDENCIES = host-python-poetry-core

$(eval $(python-package))
