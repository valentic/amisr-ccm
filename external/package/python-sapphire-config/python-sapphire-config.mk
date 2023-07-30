################################################################################
#
# python-sapphire-config
#
################################################################################

PYTHON_SAPPHIRE_CONFIG_VERSION = 1.0.4
PYTHON_SAPPHIRE_CONFIG_SOURCE = sapphire_config-$(PYTHON_SAPPHIRE_CONFIG_VERSION).tar.gz
PYTHON_SAPPHIRE_CONFIG_SITE = https://files.pythonhosted.org/packages/0e/29/52b6f494864d5cea24b80d17ab6b72d54ee4a3b245dd6009c562c462f376
PYTHON_SAPPHIRE_CONFIG_SETUP_TYPE = setuptools
PYTHON_SAPPHIRE_CONFIG_LICENSE = MIT
PYTHON_SAPPHIRE_CONFIG_LICENSE_FILES = LICENSE

$(eval $(python-package))
