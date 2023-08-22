################################################################################
#
# python-speedtest-cli
#
################################################################################

PYTHON_SPEEDTEST_CLI_VERSION = 2.1.3
PYTHON_SPEEDTEST_CLI_SOURCE = speedtest-cli-$(PYTHON_SPEEDTEST_CLI_VERSION).tar.gz
PYTHON_SPEEDTEST_CLI_SITE = https://files.pythonhosted.org/packages/85/d2/32c8a30768b788d319f94cde3a77e0ccc1812dca464ad8062d3c4d703e06
PYTHON_SPEEDTEST_CLI_SETUP_TYPE = setuptools
PYTHON_SPEEDTEST_CLI_LICENSE = Apache-2.0
PYTHON_SPEEDTEST_CLI_LICENSE_FILES = LICENSE

$(eval $(python-package))
