#!/usr/bin/env bash
# Sourced by ../restore-windows-vm-passthrough.sh. Package, host, boot, libvirt and firewall application steps.

install_packages() {
	local -a packages=(
		qemu-desktop
		libvirt
		virt-manager
		virt-viewer
		edk2-ovmf
		swtpm
		dnsmasq
		iptables-nft
		looking-glass
		spice-gtk
		usbredir
		virtio-win
		nvidia-open-dkms
		nvidia-utils
		nvidia-prime
	)

	require_command paru
	msg "Installing current virtualization, Looking Glass, and NVIDIA packages"
	paru -S --needed "${packages[@]}"
}

install_host_files() {
	sudo install -Dm644 "$TEMP_DIR/vfio.conf" /etc/modprobe.d/vfio.conf
	sudo install -Dm644 "$TEMP_DIR/nvidia-vfio-blacklist.conf" \
		/etc/modprobe.d/nvidia-vfio-blacklist.conf
	sudo install -Dm644 "$TEMP_DIR/90-nvidia-no-seat.rules" \
		/etc/udev/rules.d/90-nvidia-no-seat.rules
	sudo install -Dm644 "$TEMP_DIR/looking-glass.conf" \
		/etc/tmpfiles.d/looking-glass.conf
	sudo install -Dm755 "$TEMP_DIR/gpu-status" /usr/local/sbin/gpu-status
	sudo install -Dm755 "$TEMP_DIR/gpu-to-vfio" /usr/local/sbin/gpu-to-vfio
	sudo install -Dm755 "$TEMP_DIR/gpu-to-nvidia" \
		/usr/local/sbin/gpu-to-nvidia
	sudo install -Dm755 "$TEMP_DIR/qemu-hook" /etc/libvirt/hooks/qemu

	if [[ -f $REPO_DIR/install/nvidia/modprobe/nvidia.conf ]]; then
		sudo install -Dm644 "$REPO_DIR/install/nvidia/modprobe/nvidia.conf" \
			/etc/modprobe.d/nvidia.conf
	fi

	sudo systemd-tmpfiles --create /etc/tmpfiles.d/looking-glass.conf
	sudo udevadm control --reload-rules
}

configure_boot() {
	local entry
	local flags="amd_iommu=on iommu=pt vfio-pci.ids=$GPU_ID,$AUDIO_ID"

	[[ -d /boot/loader/entries ]] ||
		die "--configure-boot currently supports systemd-boot entries only"

	while IFS= read -r entry; do
		if sudo grep -q 'vfio-pci\.ids=' "$entry"; then
			msg "VFIO flags already exist in $entry"
			continue
		fi
		sudo sed -i -E "/^options / s|\$| $flags|" "$entry"
		msg "Added VFIO flags to $entry"
	done < <(sudo find /boot/loader/entries -maxdepth 1 -type f \
		-name '*.conf' -print)
}

enable_libvirt() {
	local -a sockets=(
		virtqemud.socket
		virtqemud-ro.socket
		virtqemud-admin.socket
		virtnetworkd.socket
		virtnetworkd-ro.socket
		virtnetworkd-admin.socket
		virtstoraged.socket
		virtstoraged-ro.socket
		virtstoraged-admin.socket
		virtnodedevd.socket
		virtnodedevd-ro.socket
		virtnodedevd-admin.socket
	)

	sudo systemctl enable --now "${sockets[@]}"
	sudo usermod -aG libvirt,kvm "$SHM_USER"

	if ! sudo virsh -c qemu:///system net-info default >/dev/null 2>&1; then
		sudo virsh -c qemu:///system net-define "$TEMP_DIR/default-network.xml"
	fi
	sudo virsh -c qemu:///system net-autostart default
	if ! sudo virsh -c qemu:///system net-info default |
		grep -q 'Active:.*yes'; then
		sudo virsh -c qemu:///system net-start default
	fi
}

configure_firewall() {
	command -v ufw >/dev/null 2>&1 || {
		warn "ufw is not installed; skipping libvirt firewall rules"
		return
	}

	sudo ufw allow in on virbr0 from "$VM_NETWORK" \
		to "$VM_GATEWAY" proto udp port 53
	sudo ufw allow in on virbr0 from "$VM_NETWORK" \
		to "$VM_GATEWAY" proto tcp port 53
	sudo ufw allow in on virbr0 proto udp to any port 67

	if [[ -n $OUTBOUND_INTERFACE ]]; then
		ip link show "$OUTBOUND_INTERFACE" >/dev/null 2>&1 ||
			die "outbound interface does not exist: $OUTBOUND_INTERFACE"
		sudo ufw route allow in on virbr0 out on "$OUTBOUND_INTERFACE" \
			from "$VM_NETWORK" comment 'libvirt NAT VM egress'
	else
		warn "no --outbound-interface supplied; NAT forwarding rule was skipped"
	fi
}

define_vm() {
	[[ -n $VM_XML ]] || return 0
	[[ -f $VM_XML ]] || die "VM XML does not exist: $VM_XML"

	if sudo virsh -c qemu:///system dominfo "$VM_NAME" >/dev/null 2>&1; then
		die "$VM_NAME is already defined; refusing to replace it"
	fi

	sudo virsh -c qemu:///system define "$VM_XML"
	sudo virsh -c qemu:///system autostart --disable "$VM_NAME"
}

validate_result() {
	printf '\n'
	msg "Host-side restore complete; checking configuration"
	sudo /usr/local/sbin/gpu-status || true
	sudo virsh -c qemu:///system net-info default
	stat /dev/shm/looking-glass
	printf '\n'
	warn "Reboot before assigning the RTX to a VM."
	warn "After reboot, verify both NVIDIA functions use vfio-pci."
	warn "Log out/in so the libvirt group membership takes effect."
	warn "The VM XML still needs a valid qcow2, NVRAM, and TPM state."
	warn "Use the recovery Markdown for the 256 MiB IVSHMEM and guest setup."
}
