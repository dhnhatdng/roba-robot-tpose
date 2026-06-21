# ROBA Robot Humanoid Proxy (T-Pose)

Mô hình 3D humanoid đại diện cho robot của **ROBA** ở tư thế **T-pose** chuẩn, được thiết kế để nộp cho **Challenge 3: Roba Robot T-Pose (3D Simple)** trên cổng **ROBA Creator Hub**.

Dự án này được thiết kế và sinh ra **hoàn toàn tự động bằng lập trình Python** (không cần cài phần mềm Blender/Maya thủ công), giúp đảm bảo tính có thể tái tạo hoàn toàn (fully reproducible) đúng theo tiêu chí của ban tổ chức.

## Cấu trúc thư mục dự án

```text
roba-robot-tpose/
├── index.glb               # [Bắt buộc] Tệp mô hình 3D preview chính (có màu sắc/PBR)
├── character_static.obj    # Mô hình tĩnh dạng OBJ
├── generate_robot.py      # Script Python lập trình sinh mô hình 3D từ các khối hình học
└── README.md               # Tài liệu hướng dẫn này
```

## Các đặc điểm kỹ thuật của mô hình
* **Tư thế (Pose)**: T-pose chuẩn (hai tay dang ngang song song mặt đất, hai chân đứng thẳng, mắt hướng thẳng).
* **Thiết kế màu sắc (Material/Color)**:
  * **Trắng kim loại / Nhựa cứng (White Armor)**: Cho các bộ phận giáp chính (đầu, ngực, vai, đùi, bắp chân).
  * **Xám đậm kim loại (Dark Grey Metal)**: Cho khung xương chịu lực và các khớp chuyển động (cổ, cột sống, khớp vai, khớp khuỷu, khớp hông, khớp gối, bàn tay, bàn chân).
  * **Xanh Cyan phát sáng (Cyan Glow)**: Cho phần kính ngắm (visor) của mắt và lõi năng lượng ở ngực để tạo điểm nhấn hiện đại đúng triết lý của ROBA.
* **Hình học**: Lưới mesh low-poly tối ưu, sạch sẽ, sẵn sàng sử dụng làm proxy cho mô phỏng vật lý hoặc game.

## Hướng dẫn tái xây dựng mô hình (Rebuild local)

1. Cài đặt Python 3.10+.
2. Cài đặt các thư viện Python cần thiết:
   ```bash
   pip install numpy trimesh scipy
   ```
3. Chạy script để sinh lại tệp mô hình 3D:
   ```bash
   python generate_robot.py
   ```
   *Sau khi chạy xong, tệp `index.glb` và `character_static.obj` mới sẽ được tạo ra tại thư mục hiện tại.*
