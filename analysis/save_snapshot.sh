#!/bin/bash
# ==============================================================================
# save_snapshot.sh - Self-contained Chameleon Cloud Instance Snapshot Script
# ==============================================================================
set -euo pipefail

# 1. Auto-elevate to root if not already root (must be before argument parsing)
if [[ $EUID -ne 0 ]]; then
  USER_HOME="${HOME:-/home/cc}"
  CONFIG_FILE="${OS_CLIENT_CONFIG_FILE:-/home/cc/.config/openstack/clouds.yaml}"
  CLOUD_NAME="${OS_CLOUD:-openstack}"
  exec sudo env \
    HOME="$USER_HOME" \
    OS_CLOUD="$CLOUD_NAME" \
    OS_CLIENT_CONFIG_FILE="$CONFIG_FILE" \
    ORIGINAL_USER="${USER:-cc}" \
    "$0" "$@"
fi

SNAPSHOT_NAME=""
DRY_RUN=false
USE_ZSTD=false

usage() {
  cat <<'USAGE_EOF'
Usage: ./save_snapshot.sh --name=<snapshot_name> [options]

Required arguments:
  --name=<name>     Name for the snapshot image in Glance

Optional arguments:
  -d, --dry-run     Print steps without executing them
  -z, --zstd        Use zstd compression instead of default zlib
  -h, --help        Show this help message
USAGE_EOF
  exit 1
}

# 2. Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name=*)
      SNAPSHOT_NAME="${1#*=}"
      shift
      ;;
    --name)
      if [[ -n "${2:-}" && ! "$2" =~ ^- ]]; then
        SNAPSHOT_NAME="$2"
        shift 2
      else
        echo "Error: --name requires a non-empty argument." >&2
        usage
      fi
      ;;
    -d|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -z|--zstd)
      USE_ZSTD=true
      shift
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Error: Unknown argument '$1'" >&2
      usage
      ;;
  esac
done

if [[ -z "$SNAPSHOT_NAME" ]]; then
  echo "Error: --name is required." >&2
  usage
fi

# 3. Locate OpenStack credentials
USER_HOME="${HOME:-/home/cc}"
if [[ -n "${OS_CLIENT_CONFIG_FILE:-}" && -f "${OS_CLIENT_CONFIG_FILE}" ]]; then
  CONFIG_FILE="${OS_CLIENT_CONFIG_FILE}"
elif [[ -f "${USER_HOME}/.config/openstack/clouds.yaml" ]]; then
  CONFIG_FILE="${USER_HOME}/.config/openstack/clouds.yaml"
elif [[ -f "/home/cc/.config/openstack/clouds.yaml" ]]; then
  CONFIG_FILE="/home/cc/.config/openstack/clouds.yaml"
else
  echo "Error: Could not locate clouds.yaml. Please ensure OpenStack credentials are configured." >&2
  exit 1
fi

export OS_CLIENT_CONFIG_FILE="$CONFIG_FILE"
export OS_CLOUD="${OS_CLOUD:-openstack}"
export HOME="$USER_HOME"

echo "=========================================="
echo "Snapshot Target : $SNAPSHOT_NAME"
echo "Clouds Config   : $OS_CLIENT_CONFIG_FILE"
echo "Cloud Account   : $OS_CLOUD"
echo "=========================================="

# Check Glance connectivity
if [[ "$DRY_RUN" == false ]]; then
  echo "Verifying OpenStack / Glance connectivity..."
  if ! openstack image list >/dev/null 2>&1; then
    echo "Error: Unable to contact OpenStack Glance. Please verify credentials." >&2
    exit 1
  fi
  echo "Glance connection OK."
fi

# Temporary paths
CC_SNAPSHOT_TAR_PATH="/tmp/snapshot.tar"
CC_SNAPSHOT_CONVERTED_PATH="/tmp/snapshot.img"
CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH="/tmp/snapshot_compressed.qcow2"
EXCLUDE_FROM="$(mktemp /tmp/snapshot-exclude.XXXXXX)"

cleanup() {
  local exit_code=$?
  if [[ "$DRY_RUN" == false ]]; then
    echo "Cleaning up temporary files..."
    rm -f "$EXCLUDE_FROM" "$CC_SNAPSHOT_TAR_PATH" "$CC_SNAPSHOT_CONVERTED_PATH" "$CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH" 2>/dev/null || true
  else
    rm -f "$EXCLUDE_FROM" 2>/dev/null || true
  fi

  # Restore ccauth token cache file permissions if executed under sudo
  if [[ -n "${ORIGINAL_USER:-}" && -d "${USER_HOME}/.cache/ccauth" ]]; then
    chown -R "${ORIGINAL_USER}:${ORIGINAL_USER}" "${USER_HOME}/.cache/ccauth" 2>/dev/null || true
  fi

  exit "$exit_code"
}
trap cleanup EXIT INT TERM

# Build exclusion file
# Note: proc/* preserves the empty /proc directory mountpoint so the system remains bootable
cat >"$EXCLUDE_FROM" <<'EXCLUDE_EOF'
tmp/*
var/tmp/*
proc/*
boot/extlinux
var/lib/cloud
var/lib/gssproxy/*.sock
var/spool/postfix
home/cc/my_mounting_point
home/cc/.cache/ccauth
var/lib/lxcfs
EXCLUDE_EOF

# Parse provenance metadata
PROVENANCE_FILE='/opt/chameleon/provenance.json'
PROVENANCE_PROPERTIES=()
if [[ -f "$PROVENANCE_FILE" ]]; then
  while IFS='=' read -r key val; do
    if [[ -n "$key" && "$key" != chameleon-supported* ]]; then
      PROVENANCE_PROPERTIES+=("--property" "provenance-${key}=${val}")
    fi
  done < <(jq -r 'to_entries[] | "\(.key)=\(.value)"' "$PROVENANCE_FILE" 2>/dev/null || true)
fi

# 1. Create root filesystem tarball
echo "==> Step 1/5: Creating filesystem tarball at $CC_SNAPSHOT_TAR_PATH..."
if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY_RUN] tar --create --file $CC_SNAPSHOT_TAR_PATH --selinux --acls --numeric-owner --one-file-system --exclude-from $EXCLUDE_FROM -C / ."
else
  declare -a TAR_ARGS=(--selinux --acls --numeric-owner --one-file-system --exclude-from "$EXCLUDE_FROM")
  n=0
  until [ $n -ge 5 ]; do
    tar --create --file "$CC_SNAPSHOT_TAR_PATH" "${TAR_ARGS[@]}" -C / . && break
    n=$((n + 1))
    sleep 15
  done
fi

# 2. Disk sizing and partition preparation
echo "==> Step 2/5: Calculating disk size and partitions..."
if [[ "$DRY_RUN" == true ]]; then
  total_disk_size=1500
  echo "[DRY_RUN] would calculate disk size with: du -d 0 -m -x --exclude-from=$EXCLUDE_FROM /"
else
  filesystem_size=$(du -d 0 -m -x --exclude-from="$EXCLUDE_FROM" / | awk '{print $1}')
  total_disk_size=$((filesystem_size + 1500))
fi
echo "Target disk image size: ${total_disk_size}MB"

LABEL="$(e2label $(findmnt -t ext4 -J | jq -r ".filesystems[].source" ) 2>/dev/null || true)"
if [[ -z "$LABEL" ]]; then
  LABEL="cloudimg-rootfs"
fi
echo "Root disk label: $LABEL"

# Bootloader target setup
ARCH=$(uname -m)
case "$ARCH" in
  "x86_64")
    GRUB_INSTALL_TARGET="x86_64-efi"
    ;;
  "aarch64"|"arm64")
    GRUB_INSTALL_TARGET="arm64-efi"
    ;;
  *)
    echo "Error: Architecture '$ARCH' unsupported!" >&2
    exit 1
    ;;
esac

GRUBNAME=$(type -p grub-install 2>/dev/null || type -p grub2-install 2>/dev/null || echo "grub-install")
GRUB_MKCONFIG=$(type -p grub-mkconfig 2>/dev/null || type -p grub2-mkconfig 2>/dev/null || echo "grub-mkconfig")

if [[ -d /boot/efi/EFI/ubuntu ]]; then
  EFI_BOOT_DIR="/boot/efi/EFI/ubuntu"
elif [[ -d /boot/efi/EFI/centos ]]; then
  EFI_BOOT_DIR="/boot/efi/EFI/centos"
else
  EFI_BOOT_DIR="/boot/efi/EFI/ubuntu"
fi

if [[ -d /boot/grub2 ]]; then
  GRUB_CFG=/boot/grub2/grub.cfg
  GRUB_ENV=/boot/grub2/grubenv
  EXTRA_CMD="&& mkdir -p $EFI_BOOT_DIR && cp $GRUB_CFG $EFI_BOOT_DIR/grub.cfg && cp $GRUB_ENV $EFI_BOOT_DIR/grubenv"
else
  GRUB_CFG=/boot/grub/grub.cfg
  EXTRA_CMD=""
fi

if [[ ! -d "$EFI_BOOT_DIR" ]]; then
  extra_options="--efi-directory=/boot/efi --target=$GRUB_INSTALL_TARGET --removable && $GRUBNAME /dev/sda"
else
  extra_options="/dev/sda"
fi

# 3. Create raw disk image with guestfish and sanitize
echo "==> Step 3/5: Building disk image with guestfish..."
if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY_RUN] guestfish -N $CC_SNAPSHOT_CONVERTED_PATH=disk:${total_disk_size}M -- ..."
  echo "[DRY_RUN] virt-sysprep -a $CC_SNAPSHOT_CONVERTED_PATH"
else
  guestfish -N "$CC_SNAPSHOT_CONVERTED_PATH=disk:${total_disk_size}M" -- \
    part-init /dev/sda gpt : \
    part-add /dev/sda primary 2048 1128447 : \
    part-add /dev/sda primary 1128448 1144831 : \
    part-add /dev/sda primary 1144832 -40 : \
    mkfs ext4 /dev/sda3 label:"$LABEL" : \
    mkfs vfat /dev/sda1 label:MKFS_ESP : \
    mount /dev/sda3 / : tar-in "$CC_SNAPSHOT_TAR_PATH" / : mount /dev/sda1 /boot/efi : \
    sh "parted /dev/sda set 2 bios_grub on" : \
    sh "parted /dev/sda set 1 esp on || true" : \
    sh "$GRUBNAME $extra_options && $GRUB_MKCONFIG -o $GRUB_CFG $EXTRA_CMD"

  echo "==> Sanitizing image with virt-sysprep..."
  virt-sysprep -a "$CC_SNAPSHOT_CONVERTED_PATH"
fi

# 4. Compress to qcow2
echo "==> Step 4/5: Converting and compressing disk image..."
if [[ "$USE_ZSTD" == true ]]; then
  COMPRESSION_TYPE="zstd"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY_RUN] qemu-img convert $CC_SNAPSHOT_CONVERTED_PATH -O qcow2 -c -o compression_type=zstd $CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH"
  else
    qemu-img convert "$CC_SNAPSHOT_CONVERTED_PATH" -O qcow2 -c -o compression_type=zstd "$CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH"
  fi
else
  COMPRESSION_TYPE="zlib"
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY_RUN] qemu-img convert $CC_SNAPSHOT_CONVERTED_PATH -O qcow2 $CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH -c"
  else
    qemu-img convert "$CC_SNAPSHOT_CONVERTED_PATH" -O qcow2 "$CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH" -c
  fi
fi

# 5. Upload to OpenStack Glance
echo "==> Step 5/5: Uploading snapshot image '$SNAPSHOT_NAME' to Glance..."
if [[ "$DRY_RUN" == true ]]; then
  echo "[DRY_RUN] openstack image create --disk-format qcow2 --container-format bare --property compression_type=$COMPRESSION_TYPE ${PROVENANCE_PROPERTIES[@]:-} $SNAPSHOT_NAME < $CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH"
else
  openstack image create \
    --disk-format qcow2 \
    --container-format bare \
    --property "compression_type=$COMPRESSION_TYPE" \
    "${PROVENANCE_PROPERTIES[@]}" \
    "$SNAPSHOT_NAME" < "$CC_SNAPSHOT_CONVERTED_COMPRESSED_PATH"
  echo "Snapshot '$SNAPSHOT_NAME' uploaded successfully!"
fi

echo "=========================================="
echo "Snapshot completed successfully: $SNAPSHOT_NAME"
echo "=========================================="
