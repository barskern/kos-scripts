KSP_MAIN_DIR := C:/Program\ Files\ (x86)/Steam/steamapps/common/Kerbal\ Space\ Program
KSP_SCRIPT_DIR := $(KSP_MAIN_DIR)/Ships/Script

KOS_SOURCE_DIR := source
KOS_MINIFY_DIR := minified

KOS_KSX_SRCS := $(wildcard $(KOS_SOURCE_DIR)/**/*.ksx) $(wildcard $(KOS_SOURCE_DIR)/**/**/*.ksx)
KOS_KS_SRCS := $(wildcard $(KOS_SOURCE_DIR)/**/*.ks) $(wildcard $(KOS_SOURCE_DIR)/**/**/*.ks)

KOS_MINIFIED_SRCS := $(patsubst $(KOS_SOURCE_DIR)/%,$(KOS_MINIFY_DIR)/%,$(KOS_KSX_SRCS:.ksx=.ks) $(KOS_KS_SRCS))

KSP_SCRIPTS := $(patsubst $(KOS_MINIFY_DIR)/%,$(KSP_SCRIPT_DIR)/%,$(KOS_MINIFIED_SRCS))

KSX_INCLUDES := -I source/

default: $(KSP_SCRIPTS)
	@echo Compiled and uploaded all scripts in source folder
.PHONY: default

$(KOS_MINIFY_DIR)/%.ks: $(KOS_SOURCE_DIR)/%.ksx
	@-mkdir "$(@D)"
	poetry run ksx --include $(KSX_INCLUDES) --single-file $< --output $@

$(KOS_MINIFY_DIR)/%.ks: $(KOS_SOURCE_DIR)/%.ks
	@-mkdir "$(@D)"
	poetry run ksx --include $(KSX_INCLUDES) --single-file $< --output $@

$(KSP_SCRIPT_DIR)/%.ks: $(KOS_MINIFY_DIR)/%.ks
# Cannot use @D due to spaces in KSP_SCRIPT_DIR
	@-mkdir "$(subst \,,$(KSP_SCRIPT_DIR))/$(dir $(patsubst $(KOS_MINIFY_DIR)/%,%,$<))"
	copy /y "$(subst /,\,$<)" "$(subst /,\,$@)"

test:
	poetry run pytest
.PHONY: test

clean:
	cd minified && git clean -fxdq
.PHONY: clean

telnet:
	telnet localhost 5410
.PHONY: telnet

ifneq ($(TARGET),)

ifneq ($(MISSION),)
push-mission: $(KOS_MINIFY_DIR)/missions/$(MISSION).ks
	@echo Pushing $(MISSION) to vessel(s) $(TARGET)...
	copy /y "$(subst /,\,$<)" "$(subst /,\,$(subst \,,$(KSP_SCRIPT_DIR))/$(TARGET)-update.ks)"
else
push-mission:
	@echo Missing MISSION variable to run 'push-mission' task
endif

ifneq ($(ACTION),)
push-action: $(KOS_MINIFY_DIR)/actions/$(ACTION).ks
	@echo Pushing $(ACTION) to vessel(s) $(TARGET)...
	copy /y "$(subst /,\,$<)" "$(subst /,\,$(subst \,,$(KSP_SCRIPT_DIR))/$(TARGET)-update.ks)"
else
push-action:
	@echo Missing ACTION variable to run 'push-action' task
endif

else

push-mission:
	@echo Missing TARGET variable to run 'push-mission' task
push-action:
	@echo Missing TARGET variable to run 'push-action' task

endif
.PHONY: push-action push-mission
