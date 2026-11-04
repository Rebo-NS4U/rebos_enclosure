#!/usr/bin/env bash
# Sourced by ../restore-windows-vm-passthrough.sh. Generate the host configuration and helper scripts in temporary storage.

write_payloads() {
	TEMP_DIR=$(mktemp -d)

	cat >"$TEMP_DIR/vfio.conf" <<EOF
# Bind the RTX GPU and its HDMI audio function to VFIO by default.
options vfio-pci ids=$GPU_ID,$AUDIO_ID disable_vga=1
softdep snd_hda_intel pre: vfio-pci
EOF

	cat >"$TEMP_DIR/nvidia-vfio-blacklist.conf" <<'EOF'
# NVIDIA is loaded explicitly by gpu-to-nvidia when PRIME mode is requested.
blacklist nouveau
blacklist nvidia
blacklist nvidia_drm
blacklist nvidia_modeset
blacklist nvidia_uvm
EOF

	cat >"$TEMP_DIR/90-nvidia-no-seat.rules" <<EOF
# Keep the dynamically rebound NVIDIA DRM card away from the desktop seat.
ACTION!="remove", SUBSYSTEM=="drm", KERNEL=="card[0-9]*", ENV{ID_PATH}=="pci-${GPU_PCI}", TAG-="seat", TAG-="master-of-seat", TAG-="uaccess"
EOF

	cat >"$TEMP_DIR/looking-glass.conf" <<EOF
f /dev/shm/looking-glass 0660 $SHM_USER $SHM_GROUP -
EOF

	cat >"$TEMP_DIR/gpu-status" <<EOF
#!/usr/bin/env bash
set -euo pipefail
GPU="$GPU_PCI"
AUDIO="$AUDIO_PCI"
VM="$VM_NAME"
driver_for() {
  if [[ -L "/sys/bus/pci/devices/\$1/driver" ]]; then
    basename "\$(readlink -f "/sys/bus/pci/devices/\$1/driver")"
  else
    echo none
  fi
}
echo "GPU driver:   \$(driver_for "\$GPU")"
echo "Audio driver: \$(driver_for "\$AUDIO")"
if command -v virsh >/dev/null 2>&1; then
  state=\$(virsh -c qemu:///system domstate "\$VM" 2>/dev/null || true)
  [[ -n \$state ]] && echo "VM state:     \$state"
fi
lspci -nnk -s "\${GPU#0000:}"
lspci -nnk -s "\${AUDIO#0000:}"
EOF

	cat >"$TEMP_DIR/gpu-to-vfio" <<EOF
#!/usr/bin/env bash
set -euo pipefail
GPU="$GPU_PCI"
AUDIO="$AUDIO_PCI"
VM="$VM_NAME"
LOCK="/run/lock/gpu-switch.lock"
driver_for() {
  if [[ -L "/sys/bus/pci/devices/\$1/driver" ]]; then
    basename "\$(readlink -f "/sys/bus/pci/devices/\$1/driver")"
  else
    echo none
  fi
}
unbind() {
  [[ -L "/sys/bus/pci/devices/\$1/driver" ]] &&
    echo "\$1" >"/sys/bus/pci/devices/\$1/driver/unbind"
}
bind_vfio() {
  modprobe vfio_pci
  echo vfio-pci >"/sys/bus/pci/devices/\$1/driver_override"
  if [[ \$(driver_for "\$1") != vfio-pci ]]; then
    unbind "\$1"
    echo "\$1" >/sys/bus/pci/drivers_probe || true
  fi
  [[ \$(driver_for "\$1") == vfio-pci ]] ||
    echo "\$1" > /sys/bus/pci/drivers/vfio-pci/bind
  [[ \$(driver_for "\$1") == vfio-pci ]] ||
    { echo "Failed to bind \$1 to vfio-pci" >&2; exit 1; }
}
[[ \${EUID:-\$(id -u)} -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
exec 9>"\$LOCK"
flock -n 9 || { echo "Another GPU switch is running." >&2; exit 1; }
state=\$(virsh -c qemu:///system domstate "\$VM" 2>/dev/null || true)
[[ \$state != running && \$state != paused ]] ||
  { echo "\$VM is already \$state." >&2; exit 0; }
systemctl stop nvidia-persistenced.service nvidia-powerd.service 2>/dev/null || true
if compgen -G "/dev/nvidia*" >/dev/null && fuser /dev/nvidia* >/dev/null 2>&1; then
  fuser -v /dev/nvidia* >&2 || true
  echo "NVIDIA is still in use." >&2
  exit 1
fi
bind_vfio "\$AUDIO"
bind_vfio "\$GPU"
for module in nvidia_drm nvidia_uvm nvidia_modeset nvidia; do
  modprobe -r "\$module" 2>/dev/null || true
done
udevadm settle --timeout=10 || true
echo "Switched RTX GPU and audio to VFIO."
EOF

	cat >"$TEMP_DIR/gpu-to-nvidia" <<EOF
#!/usr/bin/env bash
set -euo pipefail
GPU="$GPU_PCI"
AUDIO="$AUDIO_PCI"
VM="$VM_NAME"
LOCK="/run/lock/gpu-switch.lock"
driver_for() {
  if [[ -L "/sys/bus/pci/devices/\$1/driver" ]]; then
    basename "\$(readlink -f "/sys/bus/pci/devices/\$1/driver")"
  else
    echo none
  fi
}
unbind() {
  [[ -L "/sys/bus/pci/devices/\$1/driver" ]] &&
    echo "\$1" >"/sys/bus/pci/devices/\$1/driver/unbind"
}
enable_device() {
  echo on >"/sys/bus/pci/devices/\$1/power/control" 2>/dev/null || true
  echo 1 >"/sys/bus/pci/devices/\$1/enable" 2>/dev/null || true
}
[[ \${EUID:-\$(id -u)} -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }
exec 9>"\$LOCK"
flock -n 9 || { echo "Another GPU switch is running." >&2; exit 1; }
state=\$(virsh -c qemu:///system domstate "\$VM" 2>/dev/null || true)
[[ \$state != running && \$state != paused ]] ||
  { echo "Shut down \$VM before rebinding NVIDIA." >&2; exit 1; }
if [[ \$(driver_for "\$GPU") == vfio-pci && -w /sys/bus/pci/devices/\$GPU/reset ]]; then
  echo 1 >"/sys/bus/pci/devices/\$GPU/reset" || true
fi
echo nvidia >"/sys/bus/pci/devices/\$GPU/driver_override"
unbind "\$GPU"
enable_device "\$GPU"
modprobe nvidia
modprobe nvidia_modeset
modprobe nvidia_uvm
modprobe nvidia_drm
echo "\$GPU" >/sys/bus/pci/drivers_probe || true
[[ \$(driver_for "\$GPU") == nvidia ]] ||
  echo "\$GPU" >/sys/bus/pci/drivers/nvidia/bind
echo snd_hda_intel >"/sys/bus/pci/devices/\$AUDIO/driver_override"
unbind "\$AUDIO"
enable_device "\$AUDIO"
modprobe snd_hda_intel
echo "\$AUDIO" >/sys/bus/pci/drivers_probe || true
[[ \$(driver_for "\$AUDIO") == snd_hda_intel ]] ||
  echo "\$AUDIO" >/sys/bus/pci/drivers/snd_hda_intel/bind
udevadm settle --timeout=10 || true
systemctl start nvidia-powerd.service 2>/dev/null || true
echo "Switched RTX GPU and audio to Linux NVIDIA PRIME."
EOF

	cat >"$TEMP_DIR/qemu-hook" <<'EOF'
#!/usr/bin/env bash
# Keep the guest qcow2 exclusive: detach host NBD before VM start.
set -euo pipefail
VM="${1:-}"
OP="${2:-}"
PHASE="${3:-}"
[[ "$VM" == "win10-rtx3050" ]] || exit 0
case "$OP:$PHASE" in
  prepare:begin|release:end|prepare:|release:) ;;
  *) exit 0 ;;
esac
NBD=/dev/nbd0
PART=/dev/nbd0p3
QCOW=/var/lib/libvirt/images-nocow/win10-rtx3050.qcow2
connected() { [[ -s /sys/class/block/nbd0/pid ]]; }
if [[ $OP == prepare ]]; then
  while IFS= read -r target; do
    [[ -n $target ]] && umount "$target"
  done < <(findmnt -rn -S "$PART" -o TARGET 2>/dev/null || true)
  connected && qemu-nbd --disconnect "$NBD"
elif [[ -f $QCOW ]]; then
  modprobe nbd max_part=16
  connected || qemu-nbd --cache=none --connect="$NBD" "$QCOW"
  blockdev --rereadpt "$NBD" || true
  udevadm settle --timeout=10 || true
fi
EOF

	cat >"$TEMP_DIR/default-network.xml" <<EOF
<network>
  <name>default</name>
  <forward mode='nat'/>
  <bridge name='virbr0' stp='on' delay='0'/>
  <ip address='$VM_GATEWAY' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.122.2' end='192.168.122.254'/>
      <host mac='$VM_MAC' name='$VM_NAME' ip='$VM_IP'/>
    </dhcp>
  </ip>
</network>
EOF
}
