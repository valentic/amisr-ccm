################################################################################
#
# python-uc-micro-py
#
################################################################################

PYTHON_UC_MICRO_PY_VERSION = 1.0.2
PYTHON_UC_MICRO_PY_SOURCE = uc-micro-py-$(PYTHON_UC_MICRO_PY_VERSION).tar.gz
PYTHON_UC_MICRO_PY_SITE = https://files.pythonhosted.org/packages/75/db/241444fe6df6970a4c18d227193cad77fab7cec55d98e296099147de017f
PYTHON_UC_MICRO_PY_SETUP_TYPE = setuptools
PYTHON_UC_MICRO_PY_LICENSE = MIT
PYTHON_UC_MICRO_PY_LICENSE_FILES = LICENSE

$(eval $(python-package))
