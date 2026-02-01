# Thông tin về Server AI

## Thông tin CPU

### Cấu hình

**CPU Model**: Intel Xeon Platinum 8562Y+ (CPU server cao cấp)

**Số lượng**: 8 cores ( 8 sockets x 1 core/socket)

**Kiến trúc**: x86_64 (64 bit)

**Tốc độ**: ~5600 MHz (5.6 GHz BogoMIPS)

**Virtualization**: KVM ( máy ảo )

**Tính năng đặc biệt**: AVX-512, AES-NI, SHA-NI

## Thông tin GPU


## Thông tin RAM

### Cấu hình
- **Tổng RAM**: 31 GiB
- **Swap**: 0 B (không có swap)

### Mức sử dụng
- **Đã sử dụng**: 8.0 GiB (26%)
- **Còn trống**: 6.1 GiB
- **Buffer/Cache**: 17 GiB
- **Available**: 22 GiB (71%)

**Đánh giá**: RAM còn dư giả tốt, hệ thống hoạt động ổn định ✅

---

## Thông tin Disk

### Cấu hình
- **Ổ đĩa chính**: /dev/vda1 (Virtual Disk)
- **Tổng dung lượng**: 969 GB
- **Boot EFI**: /dev/vda15 (105 MB)

### Mức sử dụng
- **Đã sử dụng**: 574 GB (60%)
- **Còn trống**: 396 GB (40%)
- **Docker overlays**: Nhiều container đang chạy (9+ overlays)

**Đánh giá**: Disk sử dụng 60%, còn dư giả hợp lý. Cần theo dõi do có nhiều Docker containers ⚠️

---


# Thông tin về Server K8s-Master-1 (Production)

## Thông tin CPU

### Cấu hình
- **CPU Model**: AMD EPYC 7K62 48-Core Processor (CPU server cao cấp)
- **Số lượng**: 192 cores (2 sockets × 48 cores × 2 threads)
- **Kiến trúc**: x86_64 (64-bit)
- **Tốc độ**: 1500-2600 MHz (có Frequency boost)
- **BogoMIPS**: 5199.94
- **Cache**:
  - L1: 6 MiB (3 MiB data + 3 MiB instruction)
  - L2: 48 MiB
  - L3: 384 MiB
- **NUMA**: 2 nodes
- **Virtualization**: AMD-V
- **Tính năng**: AVX2, AES, SHA-NI, SME, SEV

### Mức sử dụng
- **CPU Idle**: 99.4% (chỉ dùng 0.7%)
- **User space**: 0.3%
- **System**: 0.4%
- **I/O Wait**: 0.0%

**Đánh giá**: CPU gần như rảnh hoàn toàn, có thể chịu thêm nhiều tải ✅

---

## Thông tin RAM

### Cấu hình
- **Tổng RAM**: 125 GiB
- **Swap**: 0 B (không có swap)

### Mức sử dụng
- **Đã sử dụng**: 27 GiB (22%)
- **Còn trống**: 2.4 GiB
- **Buffer/Cache**: 95 GiB
- **Available**: 96 GiB (77%)

**Đánh giá**: RAM dư giả rất tốt, hệ thống hoạt động ổn định ✅

---

## Thông tin Disk

### Cấu hình
- **Ổ đĩa chính**: /dev/mapper/ubuntu--vg-ubuntu--lv (LVM)
- **Tổng dung lượng**: 1.5 TB
- **Boot**: /dev/sdb2 (2.0 GB)
- **Boot EFI**: /dev/sdb1 (1.1 GB)
- **Develop Environment**: /dev/sda1 (732 GB)

### Mức sử dụng
- **Đã sử dụng**: 639 GB (45%)
- **Còn trống**: 796 GB (55%)
- **K3s containers**: Nhiều container đang chạy (30+ overlays)
- **Docker containers**: Nhiều container đang chạy (30+ overlays)
- **/develop-enviroment**: 1.2 GB / 732 GB (1%)

**Đánh giá**: Disk sử dụng 45%, còn dư giả tốt. Có nhiều K3s và Docker containers đang chạy ✅

---

# Thông tin về Server K8s-Master-2 (Production)

## Thông tin CPU

### Cấu hình
- **CPU Model**: AMD EPYC 7K62 48-Core Processor (CPU server cao cấp)
- **Số lượng**: 192 cores (2 sockets × 48 cores × 2 threads)
- **Kiến trúc**: x86_64 (64-bit)
- **Tốc độ**: 1500-2600 MHz (có Frequency boost)
- **BogoMIPS**: 5190.14
- **Cache**:
  - L1: 6 MiB (3 MiB data + 3 MiB instruction)
  - L2: 48 MiB
  - L3: 384 MiB
- **NUMA**: 2 nodes
- **Virtualization**: AMD-V
- **Tính năng**: AVX2, AES, SHA-NI, SME, SEV

### Mức sử dụng
- Chưa có data (chạy `top -bn1 | grep "Cpu(s)"` để kiểm tra)

---

## Thông tin RAM

### Cấu hình
- **Tổng RAM**: 125 GiB
- **Swap**: 0 B (không có swap)

### Mức sử dụng
- **Đã sử dụng**: 31 GiB (25%)
- **Còn trống**: 2.3 GiB
- **Buffer/Cache**: 92 GiB
- **Available**: 93 GiB (74%)

**Đánh giá**: RAM dư giả rất tốt, hệ thống hoạt động ổn định ✅

---

## Thông tin Disk

### Cấu hình
- **Ổ đĩa chính**: /dev/mapper/ubuntu--vg-ubuntu--lv (LVM)
- **Tổng dung lượng**: 1007 GB (~1 TB)
- **Boot**: /dev/sdb2 (2.0 GB)
- **Boot EFI**: /dev/sdb1 (1.1 GB)
- **MinIO Dev**: /dev/sda1 (732 GB)

### Mức sử dụng
- **Đã sử dụng**: 593 GB (62%)
- **Còn trống**: 364 GB (38%)
- **Containerd containers**: Nhiều container đang chạy (5+ pods)
- **Docker containers**: Nhiều container đang chạy (25+ overlays)
- **/minio-dev**: 81 GB / 732 GB (12%)

**Đánh giá**: Disk sử dụng 62%, cần theo dõi. Có MinIO dev storage và nhiều containers 