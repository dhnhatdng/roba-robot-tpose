# ROBA Robot Humanoid Proxy (T-Pose)

Mô hình 3D humanoid đại diện cho robot của **ROBA** ở tư thế **T-pose** chuẩn, được thiết kế để nộp cho **Challenge 3: Roba Robot T-Pose (3D Simple)** trên cổng **ROBA Creator Hub**.

Dự án được thiết kế và sinh ra **hoàn toàn tự động bằng lập trình Python** (không cần cài Blender/Maya thủ công), đảm bảo tính có thể tái tạo hoàn toàn (fully reproducible) đúng theo tiêu chí của ban tổ chức.

## Giao diện & Kết cấu thư mục dự án

```text
roba-robot-tpose/
├── index.glb        # [Bắt buộc] Tệp mô hình rigged chính cho Creator Hub preview
├── ROBA_rigged.glb  # Tệp mô hình đã gắn xương (armature + skin weights)
├── ROBA_static.glb  # Tệp mô hình tĩnh (geometry tĩnh, không có xương)
├── generate_robot.py# Script Python sinh mô hình 3D (pygltflib + numpy)
└── README.md        # Tài liệu hướng dẫn này
```

## Nội dung mô hình

Các tệp mô hình GLB chứa đầy đủ thông tin hình học và bộ xương theo yêu cầu của challenge:

| Tệp tin | Loại tài nguyên | Mô tả |
|---|---|---|
| **`ROBA_static.glb`** | **Static asset** | Dành cho hiển thị tĩnh, không chứa armature/skeleton, tối ưu hóa kích thước |
| **`ROBA_rigged.glb`** / **`index.glb`** | **Rigged asset** | Chứa bộ xương (armature) 17 bones và skin weights đầy đủ, sẵn sàng cho hoạt ảnh |

## Các đặc điểm kỹ thuật

- **Chiều cao**: ~1.85 mét.
- **Tư thế**: T-pose chuẩn (hai tay dang ngang song song mặt đất dọc trục X, chân thẳng đứng dọc trục Y, hướng nhìn về phía trước).
- **Skeleton (17 joints)**: `root`, `spine`, `chest`, `neck`, `head`, `l_shoulder`, `l_elbow`, `l_hand`, `r_shoulder`, `r_elbow`, `r_hand`, `l_hip`, `l_knee`, `l_foot`, `r_hip`, `r_knee`, `r_foot`.
- **Màu sắc (PBR Material)**:
  - **Màu xám sáng** (torso, head): `baseColor ~[0.70, 0.70, 0.75, 1.0]`, metallic=0.6, roughness=0.4.
  - **Màu xám trung tính** (limbs): `baseColor ~[0.62, 0.62, 0.67, 1.0]`, metallic=0.6, roughness=0.4.
  - **Màu xám tối** (joints, plates, hands, feet): `baseColor ~[0.55, 0.55, 0.60, 1.0]`, metallic=0.6, roughness=0.4.
- **Định dạng**: GLB (glTF 2.0 binary), tương thích WebGL/Three.js/Unity/Unreal/MuJoCo.

## Hướng dẫn tái xây dựng tài nguyên (Reproducible Build)

Yêu cầu: Python 3.10+.

```bash
pip install pygltflib numpy
python generate_robot.py
```

*Chạy lệnh trên sẽ tự động tạo ra các tệp `index.glb`, `ROBA_static.glb` và `ROBA_rigged.glb` tại thư mục hiện tại.*
