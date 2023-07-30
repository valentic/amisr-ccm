################################################################################
#
# python-pytimeparse2
#
################################################################################

PYTHON_PYTIMEPARSE2_VERSION = 1.7.1
PYTHON_PYTIMEPARSE2_SOURCE = pytimeparse2-$(PYTHON_PYTIMEPARSE2_VERSION).tar.gz
PYTHON_PYTIMEPARSE2_SITE = https://files.pythonhosted.org/packages/19/10/cc63fecd69905eb4d300fe71bd580e4a631483e9f53fdcb8c0ad345ce832
PYTHON_PYTIMEPARSE2_SETUP_TYPE = setuptools
PYTHON_PYTIMEPARSE2_LICENSE = MIT
PYTHON_PYTIMEPARSE2_LICENSE_FILES = LICENSE.rst

$(eval $(python-package))
