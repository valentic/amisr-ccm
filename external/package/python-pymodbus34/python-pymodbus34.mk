################################################################################
#
# python-pymodbus34
#
################################################################################

PYTHON_PYMODBUS34_VERSION = 3.4.1
PYTHON_PYMODBUS34_SOURCE = pymodbus-$(PYTHON_PYMODBUS34_VERSION).tar.gz
PYTHON_PYMODBUS34_SITE = https://files.pythonhosted.org/packages/08/06/7f0741e5e1ff69b021203486193a78527fc7321ebf1b0031451182b9df7c
PYTHON_PYMODBUS34_SETUP_TYPE = setuptools
PYTHON_PYMODBUS34_LICENSE = BSD-3-Clause
PYTHON_PYMODBUS34_LICENSE_FILES = LICENSE

$(eval $(python-package))
