#!/usr/bin/env bash
#
# Rebuild the host side of the former win10-rtx3050 VFIO/Looking Glass setup.
#
# This script DOES NOT recreate the deleted Windows qcow2, NVRAM, TPM state,
# Windows installation, or Looking Glass Host configuration inside Windows.
# Read windows-vm-passthrough-looking-glass.md before applying it.
#
# Safe default: without --apply this script performs validation and prints what
# it would do. It never contains or stores a sudo password.

set -euo pipefail
IFS=$'\n\t'

VM_NAME="win10-rtx3050"
GPU_PCI="0000:01:00.0"
GPU_ID="10de:25a2"
AUDIO_PCI="0000:01:00.1"
AUDIO_ID="10de:2291"
USB_CONTROLLER_PCI="0000:06:00.4"
SHM_USER="radhey"
SHM_GROUP="kvm"
SHM_SIZE_MIB="256"
VM_MAC="52:54:00:1a:cd:bd"
VM_IP="192.168.122.50"
VM_NETWORK="192.168.122.0/24"
VM_GATEWAY="192.168.122.1"
REPO_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)

APPLY=0
CONFIGURE_BOOT=0
VM_XML=""
OUTBOUND_INTERFACE=""
TEMP_DIR=""

msg() {
	printf '==> %s\n' "$*"
}

warn() {
	printf 'WARNING: %s\n' "$*" >&2
}

die() {
	printf 'ERROR: %s\n' "$*" >&2
	exit 1
}

usage() {
	cat <<'EOF'
Usage:
  restore-windows-vm-passthrough.sh [options]

Options:
  --apply                 Make changes. Without this, only validate and preview.
  --configure-boot        Add AMD IOMMU/VFIO flags to systemd-boot entries.
  --vm-xml PATH           Define a previously exported inactive libvirt XML.
  --outbound-interface IF Interface used for libvirt NAT, e.g. wlan0.
  -h, --help              Show this help.

Examples:
  ./docs/restore-windows-vm-passthrough.sh
  ./docs/restore-windows-vm-passthrough.sh --apply --configure-boot
  ./docs/restore-windows-vm-passthrough.sh --apply \
    --vm-xml /path/to/win10-rtx3050.xml --outbound-interface wlan0

The exact former setup is documented in:
  docs/windows-vm-passthrough-looking-glass.md
EOF
}

cleanup() {
	if [[ -n ${TEMP_DIR:-} && -d $TEMP_DIR ]]; then
		rm -r -- "$TEMP_DIR"
	fi
}

parse_args() {
	while (($#)); do
		case "$1" in
			--apply)
				APPLY=1
				shift
				;;
			--configure-boot)
				CONFIGURE_BOOT=1
				shift
				;;
			--vm-xml)
				[[ $# -ge 2 ]] || die "--vm-xml requires a path"
				VM_XML=$2
				shift 2
				;;
			--outbound-interface)
				[[ $# -ge 2 ]] || die "--outbound-interface requires a name"
				OUTBOUND_INTERFACE=$2
				shift 2
				;;
			-h|--help)
				usage
				exit 0
				;;
			*)
				die "unknown option: $1"
				;;
		esac
	done
}

source "$REPO_DIR/docs/windows-vm-passthrough/validation.sh"
source "$REPO_DIR/docs/windows-vm-passthrough/payloads.sh"
source "$REPO_DIR/docs/windows-vm-passthrough/host.sh"

main() {
	require_command lspci
	require_command readlink
	validate_hardware
	preview

	if [[ $APPLY -ne 1 ]]; then
		printf '\nDry run only. Re-run with --apply to make changes.\n'
		exit 0
	fi

	printf '\nType RESTORE-PASSTHROUGH to continue: '
	read -r confirmation
	[[ $confirmation == RESTORE-PASSTHROUGH ]] ||
		die "confirmation did not match"

	sudo -v
	write_payloads
	install_packages
	install_host_files
	if [[ $CONFIGURE_BOOT -eq 1 ]]; then
		configure_boot
	fi
	enable_libvirt
	configure_firewall
	define_vm
	sudo mkinitcpio -P
	validate_result
}

if [[ ${BASH_SOURCE[0]} == "$0" ]]; then
	trap cleanup EXIT
	parse_args "$@"
	main
fi
