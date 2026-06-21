# ROBA Robot Humanoid Proxy (T-Pose)

Mô hình 3D humanoid đại diện cho robot của **ROBA** ở tư thế **T-pose** chuẩn, được thiết kế để nộp cho **Challenge 3: Roba Robot T-Pose (3D Simple)** trên cổng **ROBA Creator Hub**.

Dự án được thiết kế và sinh ra **hoàn toàn tự động bằng lập trình Python** (không cần cài Blender/Maya thủ công), đảm bảo tính có thể tái tạo hoàn toàn (fully reproducible) đúng theo tiêu chí của ban tổ chức.

## Cấu trúc thư mục dự án

```text
roba-robot-tpose/
├── index.glb                    # [Bắt buộc] Tệp mô hình 3D chính: có đủ geometry tĩnh + skeleton rig
├── generate_robot.py            # Script Python sinh mô hình 3D (pygltflib + numpy)
├── roba_robot_blender_script.py # Script thay thế cho Blender (headless hoặc Scripting tab)
└── README.md                    # Tài liệu hướng dẫn này
```

## Nội dung file `index.glb`

File GLB chứa **đầy đủ cả hai dạng asset** theo yêu cầu của challenge:

| Nội dung | Mô tả |
|---|---|
| **Static geometry** | Toàn bộ bộ phận cơ thể robot được dựng bằng hình học cơ bản (hộp, trụ, cầu) với màu PBR |
| **Rigged version** | Bộ xương (skeleton) 15 bones theo chuẩn humanoid, skin weights gắn mỗi vertex vào bone tương ứng |

## Các đặc điểm kỹ thuật

- **Tư thế**: T-pose chuẩn (hai tay dang ngang song song mặt đất, hai chân thẳng)
- **Skeleton**: 15 bones — Hips → Spine → Chest → Neck → Head; Vai/Khuỷu/Cổ tay (2 bên); Hông/Gối (2 bên)
- **Màu sắc (PBR Material)**:
  - **Trắng bạc (White Armor)**: Đầu, ngực, vai, cánh tay, đùi, bắp chân
  - **Xám đậm (Dark Grey Metal)**: Cổ, cột sống, các khớp
  - **Xanh Cyan (Cyan Glow)**: Kính mắt (visor) và lõi năng lượng ngực
- **Định dạng**: GLB (glTF 2.0 binary), tương thích WebGL/Three.js/Unity/Unreal

## Hướng dẫn tái xây dựng (Reproducible Build)

### Cách 1: Python thuần (không cần Blender)

```bash
pip install pygltflib numpy
python generate_robot.py
```

*Tệp `index.glb` mới sẽ được tạo tại thư mục hiện tại.*

### Cách 2: Blender (headless CLI)

```bash
blender --background --python roba_robot_blender_script.py
```

*Tạo ra thêm `ROBA_Robot_Static.glb`, `ROBA_Robot_Rigged.glb`, và các file FBX.*
