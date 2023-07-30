################################################################################
#
# python-mdit-py-plugins
#
################################################################################

PYTHON_MDIT_PY_PLUGINS_VERSION = 0.4.0
PYTHON_MDIT_PY_PLUGINS_SOURCE = mdit_py_plugins-$(PYTHON_MDIT_PY_PLUGINS_VERSION).tar.gz
PYTHON_MDIT_PY_PLUGINS_SITE = https://files.pythonhosted.org/packages/b4/db/61960d68d5c39ff0dd48cb799a39ae4e297f6e9b96bf2f8da29d897fba0c
PYTHON_MDIT_PY_PLUGINS_SETUP_TYPE = flit
PYTHON_MDIT_PY_PLUGINS_LICENSE = MIT
PYTHON_MDIT_PY_PLUGINS_LICENSE_FILES = LICENSE mdit_py_plugins/texmath/LICENSE mdit_py_plugins/front_matter/LICENSE mdit_py_plugins/footnote/LICENSE mdit_py_plugins/deflist/LICENSE mdit_py_plugins/container/LICENSE mdit_py_plugins/admon/LICENSE

$(eval $(python-package))
