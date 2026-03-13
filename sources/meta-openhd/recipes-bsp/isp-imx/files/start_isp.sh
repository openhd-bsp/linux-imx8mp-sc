#!/bin/sh
#
# Start the isp_media_server in the configuration for Basler daA3840-30mc
#
# (c) Basler 2020
# (c) NXP 2020-2022
#

RUNTIME_DIR="$( cd "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
count_compatible() {
	PATTERN="$1"
	find /sys/firmware/devicetree/base -type f -name compatible 2>/dev/null \
		| grep -E '/i2c(@|-)' \
		| while IFS= read -r COMPAT_FILE; do
			grep -aq "$PATTERN" "$COMPAT_FILE" && echo "$COMPAT_FILE"
		done \
		| wc -l
}

NR_DEVICE_TREE_BASLER=$(count_compatible "basler-camera-vvcam")
NR_DEVICE_TREE_OV5640=$(count_compatible "ov5640")
NR_DEVICE_TREE_OS08A20=$(count_compatible "os08a20")


# check if the basler device has been enabled in the device tree
if [ $NR_DEVICE_TREE_BASLER -eq 1 ]; then

	echo "Starting isp_media_server for Single Basler daA3840-30mc"

	cd $RUNTIME_DIR

	if [ $NR_DEVICE_TREE_OV5640 -eq 0 ]; then

		# Default configuration for Basler daA3840-30mc: basler_4k
		# Available configurations: basler_4k, basler_1080p60, basler_4khdr, basler_1080p60hdr
		exec ./run.sh -c basler_4k -lm

	elif [ $NR_DEVICE_TREE_OV5640 -eq 1 ]; then

		# Default configuration for Basler daA3840-30mc: basler_1080p60
		# Available configurations: basler_1080p60, basler_1080p60hdr
		exec ./run.sh -c basler_1080p60 -lm
	fi

elif [ $NR_DEVICE_TREE_BASLER -eq 2 ]; then

	echo "Starting isp_media_server for Dual Basler daA3840-30mc"

	cd $RUNTIME_DIR
	# Default configuration for Basler daA3840-30mc: dual_basler_1080p60
	# Available configurations: dual_basler_1080p60, dual_basler_1080p60hdr
	exec ./run.sh -c dual_basler_1080p60 -lm
# check if the os08a20 device has been enabled in the device tree
elif [ $NR_DEVICE_TREE_OS08A20 -eq 1 ]; then

	echo "Starting isp_media_server for Single os08a20"

	cd $RUNTIME_DIR

	if [ $NR_DEVICE_TREE_OV5640 -eq 0 ]; then

		# Default configuration for Os08a20: Os08a20_4k
		# Available configurations: Os08a20_4k, Os08a20_1080p60, Os08a20_4khdr, Os08a20_1080p30hdr
		exec ./run.sh -c os08a20_1080p60 -lm

	elif [ $NR_DEVICE_TREE_OV5640 -eq 1 ]; then

		# Default configuration for Os08a20: Os08a20_1080p60
		# Available configurations: Os08a20_1080p60, Os08a20_1080p30hdr
		exec ./run.sh -c os08a20_1080p60 -lm
	fi

elif [ $NR_DEVICE_TREE_OS08A20 -eq 2 ]; then

	echo "Starting isp_media_server for Dual os08a20"

	cd $RUNTIME_DIR
	# Default configuration for Os08a20: dual_Os08a20_1080p60
	# Available configurations: dual_Os08a20_1080p60, dual_Os08a20_1080p30hdr
	exec ./run.sh -c dual_os08a20_1080p60 -lm

else
	# no device tree found exit with code no device or address
	echo "No device tree found for Basler camera or os08a20, check dtb file!" >&2
	exit 6
fi
