################################################################################
#
# datatransport
#
################################################################################

DATATRANSPORT_VERSION = 2.0.133
DATATRANSPORT_SITE = http://isr.sri.com/ftp/valentic/packages
DATATRANSPORT_SOURCE = transport-$(DATATRANSPORT_VERSION).tar.gz
DATATRANSPORT_LICENSE = GPLv2+ 
DATATRANSPORT_LICENSE_FILES = LICENSE 
DATATRANSPORT_DEPENDENCIES += host-python 

DATATRANSPORT_BASEDIR=/opt/transport

DATATRANSPORT_CONF_OPTS = \
	--with-ctlinnd=$(INN2_BASEDIR)/bin/ctlinnd \
	--prefix=$(DATATRANSPORT_BASEDIR)/ \
	--exec-prefix=$(DATATRANSPORT_BASEDIR) \
	--with-hostname=fcu \
	--disable-initd \
	--disable-chown \
	--disable-defaultgroups

define DATATRANSPORT_INSTALL_INIT_SYSV
	$(INSTALL) -D -m 0755 $(@D)/support/S61transport \
		$(TARGET_DIR)/etc/init.d/S71transport
endef

define DATATRANSPORT_INSTALL_EXTRA
	$(INSTALL) -D -m 0644 $(@D)/support/_transportctl \
		-t $(TARGET_DIR)/etc/bash_completion.d
endef

DATATRANSPORT_POST_INSTALL_TARGET_HOOKS += DATATRANSPORT_INSTALL_EXTRA

define DATATRANSPORT_USERS
	transport -1 transport -1 ! $(DATATRANSPORT_BASEDIR) /bin/sh dialout,lock,wheel
endef

define DATATRANSPORT_PERMISSIONS
	$(DATATRANSPORT_BASEDIR) r 775 transport transport - - - - -
	$(DATATRANSPORT_BASEDIR)/etc d 2775 transport transport - - - - -
	$(DATATRANSPORT_BASEDIR)/groups d 2775 transport transport - - - - -
endef

$(eval $(autotools-package))
