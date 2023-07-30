################################################################################
#
# python-linkify-it-py
#
################################################################################

PYTHON_LINKIFY_IT_PY_VERSION = 2.0.2
PYTHON_LINKIFY_IT_PY_SOURCE = linkify-it-py-$(PYTHON_LINKIFY_IT_PY_VERSION).tar.gz
PYTHON_LINKIFY_IT_PY_SITE = https://files.pythonhosted.org/packages/8d/fd/73bb30ec2b3cd952fe139a79a40ce5f5fd0280dd2cc1de94c93ea6a714d2
PYTHON_LINKIFY_IT_PY_SETUP_TYPE = setuptools
PYTHON_LINKIFY_IT_PY_LICENSE = MIT
PYTHON_LINKIFY_IT_PY_LICENSE_FILES = LICENSE

$(eval $(python-package))
