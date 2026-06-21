# ROBA Robot Humanoid Proxy (T-Pose)

Mô hình 3D humanoid đại diện cho robot của **ROBA** ở tư thế **T-pose** chuẩn, được thiết kế để nộp cho **Challenge 3: Roba Robot T-Pose (3D Simple)** trên cổng **ROBA Creator Hub**.

Dự án được thiết kế và sinh ra **hoàn toàn tự động bằng lập trình Python** (không cần cài Blender/Maya thủ công), đảm bảo tính có thể tái tạo hoàn toàn (fully reproducible) đúng theo tiêu chí của ban tổ chức.

## Cấu trúc thư mục dự án

```text
roba-robot-tpose/
├── index.glb                    # [Bắt buộc] Tệp mô hình rigged chính cho Creator Hub preview
├── ROBA_static.glb              # Tệp mô hình tĩnh (geometry tĩnh, không có xương)
├── ROBA_rigged.glb              # Tệp mô hình đã gắn xương (armature + skin weights)
├── generate_robot.py            # Script Python sinh mô hình 3D (pygltflib + numpy)
├── roba_robot_blender_script.py # Script thay thế cho Blender (headless hoặc Scripting tab)
└── README.md                    # Tài liệu hướng dẫn này
```

## Nội dung mô hình

Các tệp mô hình GLB chứa đầy đủ thông tin hình học và bộ xương theo yêu cầu của challenge:

| Tệp tin | Loại tài nguyên | Mô tả |
|---|---|---|
| **`ROBA_static.glb`** | **Static asset** | Dành cho hiển thị tĩnh, không chứa armature/skeleton, tối ưu hóa kích thước |
| **`ROBA_rigged.glb`** / **`index.glb`** | **Rigged asset** | Chứa bộ xương (armature) 15 bones và skin weights đầy đủ, sẵn sàng cho hoạt ảnh |

## Các đặc điểm kỹ thuật

- **Tư thế**: T-pose chuẩn (hai tay dang ngang song song mặt đất dọc trục X, hai chân đứng thẳng dọc trục Z, mặt hướng -Y).
- **Skeleton**: 15 bones — Hips → Spine → Chest → Neck → Head; Vai/Khuỷu/Cổ tay (2 bên); Hông/Gối (2 bên).
- **Màu sắc (PBR Material)**:
  - **Trắng bạc/Xám sáng (White/Light Gray Plating)**: Thân chính, Đầu, Cánh tay trên, Đùi.
  - **Xanh Cyan (Cyan Glow Accent)**: Các khớp nối (cổ, vai, khuỷu, cổ tay, hông, gối), tấm ốp ngực (chest panel) và kính mắt (visor).
- **Định dạng**: GLB (glTF 2.0 binary) và FBX (thông qua Blender script), tương thích WebGL/Three.js/Unity/Unreal/MuJoCo.

## Hướng dẫn tái xây dựng (Reproducible Build)

### Cách 1: Python thuần (không cần Blender)

```bash
pip install pygltflib numpy
python generate_robot.py
```

*Tạo ra các tệp `index.glb`, `ROBA_static.glb` và `ROBA_rigged.glb` tại thư mục hiện tại.*

### Cách 2: Blender (headless CLI)

Nếu bạn có Blender trên máy và cần xuất cả phiên bản **FBX**:

```bash
blender --background --python roba_robot_blender_script.py
```

*Tạo ra thêm `ROBA_static.fbx`, `ROBA_static.glb`, `ROBA_rigged.fbx` và `ROBA_rigged.glb`.*
