#!/bin/bash
#
# Verify that every option declared in a defconfig fragment actually made it
# into a generated .config. This catches "silent drift": an option that gets
# dropped because an unmet dependency (or a base-defconfig change) prevented it
# from being applied, which merge_config.sh does not fail on.
#
# Usage: tools/check-fragment.sh <fragment> <.config>
#   e.g. tools/check-fragment.sh arch/arm64/configs/vanillaKernel-defconfig out/.config

set -euo pipefail

FRAGMENT="${1:-arch/arm64/configs/vanillaKernel-defconfig}"
CONFIG="${2:-out/.config}"

if [ ! -f "$FRAGMENT" ]; then
    echo "Error: fragment '$FRAGMENT' not found" >&2
    exit 2
fi
if [ ! -f "$CONFIG" ]; then
    echo "Error: config '$CONFIG' not found (build the config first)" >&2
    exit 2
fi

fail=0
checked=0

while IFS= read -r line; do
    # Normalise: strip leading/trailing whitespace
    line="${line#"${line%%[![:space:]]*}"}"

    if [[ "$line" =~ ^CONFIG_[A-Za-z0-9_]+= ]]; then
        # Expected to be set to a specific value
        key="${line%%=*}"
        if ! grep -qxF "$line" "$CONFIG"; then
            actual=$(grep -E "^$key=|^# $key is not set" "$CONFIG" || echo "# $key is absent")
            echo "MISMATCH: fragment wants '$line'"
            echo "             .config has '$actual'"
            fail=1
        fi
        checked=$((checked + 1))
    elif [[ "$line" =~ ^#[[:space:]]CONFIG_[A-Za-z0-9_]+[[:space:]]is[[:space:]]not[[:space:]]set ]]; then
        # Expected to be disabled
        key=$(echo "$line" | awk '{print $2}')
        if grep -qE "^$key=" "$CONFIG"; then
            actual=$(grep -E "^$key=" "$CONFIG")
            echo "MISMATCH: fragment wants '$key' disabled"
            echo "             .config has '$actual'"
            fail=1
        fi
        checked=$((checked + 1))
    fi
done < "$FRAGMENT"

echo "Checked $checked option(s) from $FRAGMENT against $CONFIG"

if [ "$fail" -ne 0 ]; then
    echo "::error::Fragment options were dropped from the final .config (see MISMATCH above)"
    exit 1
fi

echo "All fragment options applied cleanly."
