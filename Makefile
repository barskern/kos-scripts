KSP_MAIN_DIR := C:/Program\ Files\ (x86)/Steam/steamapps/common/Kerbal\ Space\ Program
KSP_SCRIPT_DIR := $(KSP_MAIN_DIR)/Ships/Script

KOS_SOURCE_DIR := source
KOS_MINIFY_DIR := minified

KOS_ACTION_SRCS := $(wildcard $(KOS_SOURCE_DIR)/actions/*.ksx)
KOS_LIB_SRCS := $(wildcard $(KOS_SOURCE_DIR)/lib/*.ksx)
KOS_BOOT_SRCS := $(wildcard $(KOS_SOURCE_DIR)/boot/*.ksx)

KOS_MINIFIED_BOOT_SRCS := $(patsubst $(KOS_SOURCE_DIR)/%,$(KOS_MINIFY_DIR)/%,$(KOS_BOOT_SRCS:.ksx=.ks))

KSP_SCRIPTS := $(patsubst $(KOS_MINIFY_DIR)/%,$(KSP_SCRIPT_DIR)/%,$(KOS_MINIFIED_BOOT_SRCS))

KSX_INCLUDES := -I source/

KSX_FLAGS := --transpile-only --include $(KSX_INCLUDES)

default: $(KSP_SCRIPTS)
	@echo Compiled and uploaded all scripts in source folder
.PHONY: default

$(KOS_MINIFY_DIR)/%.ks: $(KOS_SOURCE_DIR)/%.ksx $(KOS_LIB_SRCS) $(KOS_ACTION_SRCS)
	@-mkdir "$(@D)"
	poetry run ksx $(KSX_FLAGS) --single-file $< --output $@

$(KOS_MINIFY_DIR)/%.ks: $(KOS_SOURCE_DIR)/%.ks $(KOS_LIB_SRCS) $(KOS_ACTION_SRCS)
	@-mkdir "$(@D)"
	poetry run ksx $(KSX_FLAGS) --single-file $< --output $@

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

ifneq ($(TEST),)
TARGET ?= code_tests
push-tests: $(KOS_MINIFY_DIR)/tests/$(TEST)-tests.ks
	@echo Pushing test for $(TEST) to vessel(s) $(TARGET)...
	copy /y "$(subst /,\,$<)" "$(subst /,\,$(subst \,,$(KSP_SCRIPT_DIR))/$(TARGET)-update.ks)"
else
push-tests:
	@echo Missing TEST variable to run 'push-tests' task
endif


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
.PHONY: push-action push-mission push-tests

.SECONDARY: