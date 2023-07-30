################################################################################
#
# python-textual
#
################################################################################

PYTHON_TEXTUAL_VERSION = 0.30.0
PYTHON_TEXTUAL_SOURCE = textual-$(PYTHON_TEXTUAL_VERSION).tar.gz
PYTHON_TEXTUAL_SITE = https://files.pythonhosted.org/packages/f8/7e/0917924079aeab58c18ac8d34c0f318daa3a956f1d6caff81b334f411076
PYTHON_TEXTUAL_SETUP_TYPE = pep517
PYTHON_TEXTUAL_LICENSE = MIT
PYTHON_TEXTUAL_LICENSE_FILES = LICENSE
PYTHON_TEXTUAL_DEPENDENCIES = host-python-poetry-core

$(eval $(python-package))
