#!/usr/bin/env bash
# Sourced by ../restore-windows-vm-passthrough.sh. Hardware checks and read-only recovery preview.

require_command() {
	command -v "$1" >/dev/null 2>&1 || die "required command is missing: $1"
}

pci_id() {
	local device=$1
	local vendor product

	[[ -r /sys/bus/pci/devices/$device/vendor ]] ||
		die "PCI device is missing: $device"
	[[ -r /sys/bus/pci/devices/$device/device ]] ||
		die "PCI device ID is unreadable: $device"

	vendor=$(<"/sys/bus/pci/devices/$device/vendor")
	product=$(<"/sys/bus/pci/devices/$device/device")
	printf '%s:%s\n' "${vendor#0x}" "${product#0x}"
}

iommu_group() {
	local device=$1
	local link="/sys/bus/pci/devices/$device/iommu_group"

	[[ -L $link ]] || die "$device has no IOMMU group"
	basename "$(readlink -f "$link")"
}

validate_hardware() {
	local actual_gpu actual_audio gpu_group audio_group

	actual_gpu=$(pci_id "$GPU_PCI")
	actual_audio=$(pci_id "$AUDIO_PCI")
	[[ $actual_gpu == "$GPU_ID" ]] ||
		die "$GPU_PCI is $actual_gpu, expected $GPU_ID"
	[[ $actual_audio == "$AUDIO_ID" ]] ||
		die "$AUDIO_PCI is $actual_audio, expected $AUDIO_ID"

	gpu_group=$(iommu_group "$GPU_PCI")
	audio_group=$(iommu_group "$AUDIO_PCI")
	[[ $gpu_group == "$audio_group" ]] ||
		die "GPU and audio are no longer in the same IOMMU group"

	msg "RTX GPU and audio IDs match the former setup"
	msg "GPU/audio IOMMU group: $gpu_group"

	if [[ -d /sys/bus/pci/devices/$USB_CONTROLLER_PCI ]]; then
		msg "Optional USB controller group: $(iommu_group "$USB_CONTROLLER_PCI")"
	else
		warn "optional USB controller $USB_CONTROLLER_PCI is missing"
	fi

	if command -v bootctl >/dev/null 2>&1; then
		bootctl status 2>/dev/null |
			grep -E 'Firmware:|Secure Boot:|TPM2 Support:' || true
	fi
}

preview() {
	cat <<EOF

This will restore:
  - VFIO default binding for $GPU_PCI and $AUDIO_PCI
  - dynamic gpu-to-vfio / gpu-to-nvidia helpers
  - NVIDIA no-seat rule while dynamically rebound
  - libvirt modular sockets and default NAT network
  - DHCP reservation $VM_IP for $VM_MAC
  - Looking Glass shared memory: ${SHM_SIZE_MIB} MiB in the VM XML,
    with /dev/shm/looking-glass owned by $SHM_USER:$SHM_GROUP
  - the qcow2/NBD exclusivity hook

It will not restore:
  - the deleted Windows qcow2
  - OVMF NVRAM or virtual TPM state
  - Windows, GPU drivers, IVSHMEM driver, or Looking Glass Host in the guest
  - the old Waybar VM button
EOF

	if [[ $CONFIGURE_BOOT -eq 1 ]]; then
		printf '%s\n' \
			"  - systemd-boot entries WILL receive AMD IOMMU and VFIO flags"
	else
		printf '%s\n' \
			"  - systemd-boot entries will not be edited (no --configure-boot)"
	fi

	if [[ -n $VM_XML ]]; then
		printf '  - libvirt XML to define: %s\n' "$VM_XML"
	fi
}
