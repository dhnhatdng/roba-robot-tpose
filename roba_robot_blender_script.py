"""
ROBA Creator Hub — Robot T-Pose Generator
==========================================
Script chạy bên trong Blender (Scripting tab hoặc CLI headless).

Cách dùng:
  1. Mở Blender > tab "Scripting" > New > dán toàn bộ nội dung file này > Run Script.
     HOẶC chạy từ terminal (headless, không cần GUI):
       blender --background --python roba_robot_blender_script.py

  2. Kết quả export vào cùng thư mục với file .blend (hoặc thư mục làm việc khi headless):
       - ROBA_Robot_Static.glb / .fbx   -> hình học tĩnh, không có armature
       - ROBA_Robot_Rigged.glb  / .fbx  -> armature + skin weights, tư thế chữ T

Thiết kế: low-poly humanoid cao 1.7m (7.5 đầu), T-pose chuẩn:
  - Tay duỗi thẳng ngang vai (trục +X bên trái, -X bên phải), lòng bàn tay úp xuống
  - Chân khép thẳng, đứng tự nhiên
  - Đầu nhìn thẳng theo hướng -Y
"""

import bpy
import math
import os

# ────────────────────────────────────────────────────────────────────────────
# 0. DỌN SCENE
# ────────────────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
    for item in list(block):
        if item.users == 0:
            block.remove(item)

# ────────────────────────────────────────────────────────────────────────────
# 1. TỈ LỆ HUMANOID (đơn vị: mét) — cao ~1.7 m, 7.5 đầu
# ────────────────────────────────────────────────────────────────────────────
TOTAL_HEIGHT = 1.70
HEAD_H       = TOTAL_HEIGHT / 7.5   # ≈ 0.2267 m

NECK_H       = HEAD_H * 0.25
TORSO_H      = HEAD_H * 2.6
PELVIS_H     = HEAD_H * 0.9
UPPER_ARM_L  = HEAD_H * 1.6
LOWER_ARM_L  = HEAD_H * 1.4
HAND_L       = HEAD_H * 0.7
UPPER_LEG_L  = HEAD_H * 2.0
LOWER_LEG_L  = HEAD_H * 1.9
FOOT_L       = HEAD_H * 0.9

SHOULDER_W   = HEAD_H * 1.9    # khoảng cách tâm 2 vai
HIP_W        = HEAD_H * 1.1
LIMB_R       = HEAD_H * 0.22   # bán kính hình trụ chi

# Toạ độ Z các mốc quan trọng (trục Z hướng lên)
GROUND_Z  = 0.0
ANKLE_Z   = GROUND_Z + FOOT_L * 0.3          # cổ chân cách đất 1 chút
KNEE_Z    = ANKLE_Z  + LOWER_LEG_L
PELVIS_Z  = KNEE_Z   + UPPER_LEG_L
TORSO_Z   = PELVIS_Z + PELVIS_H
NECK_Z    = TORSO_Z  + TORSO_H
HEAD_Z    = NECK_Z   + NECK_H + HEAD_H * 0.5  # tâm đầu

# Toạ độ Z vai (gắn cánh tay) — gần phía trên ngực
SHOULDER_Z = TORSO_Z + TORSO_H * 0.87

# ── Màu sắc ──────────────────────────────────────────────────────────────────
ROBA_WHITE  = (0.90, 0.90, 0.90, 1.0)   # Thân chính (Light gray / White plating)
ROBA_CYAN   = (0.00, 0.85, 1.00, 1.0)   # Accent color (Cyan) trên các khớp, ngực, visor

# ────────────────────────────────────────────────────────────────────────────
# 2. HÀM TẠO HÌNH HỌC
# ────────────────────────────────────────────────────────────────────────────
def make_material(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value  = 0.4
        bsdf.inputs["Metallic"].default_value   = 0.3
    return mat

mat_body   = make_material("ROBA_Body",   ROBA_WHITE)
mat_joint  = make_material("ROBA_Joint",  ROBA_CYAN)
mat_accent = make_material("ROBA_Accent", ROBA_CYAN)


def add_box(name, size, location, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def add_cylinder(name, radius, depth, location, rotation=(0, 0, 0), mat=None):
    """
    Blender tạo cylinder theo trục Z mặc định.
    Để dựng theo trục X (tay T-pose):  rotation = (0, pi/2, 0)
    Để dựng theo trục Y:                rotation = (pi/2, 0, 0)
    """
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth,
        location=location, rotation=rotation, vertices=12
    )
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


def add_sphere(name, radius, location, mat=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location, segments=16, ring_count=10
    )
    obj = bpy.context.active_object
    obj.name = name
    if mat:
        obj.data.materials.clear()
        obj.data.materials.append(mat)
    return obj


# ────────────────────────────────────────────────────────────────────────────
# 3. DỰNG HÌNH HỌC — TƯ THẾ CHỮ T
# ────────────────────────────────────────────────────────────────────────────
#
#  Quy ước trục (Blender):
#    X → phải (Left-arm ở +X, Right-arm ở -X nhìn từ trước)
#    Y → sâu vào màn hình
#    Z → lên
#
#  Tư thế chữ T:
#    • Cả 2 cánh tay duỗi thẳng ngang, song song mặt đất (dọc theo trục X)
#    • Cylinder tay xoay  rotation=(0, pi/2, 0)  để đặt dọc theo trục X
#    • Chân thẳng đứng  → cylinder giữ mặc định (dọc Z), không cần xoay

HALF_PI = math.pi / 2    # 90° — xoay cylinder thành nằm ngang theo X

parts = []

# ── ĐẦU ──────────────────────────────────────────────────────────────────────
parts.append(add_sphere("Head", 0.14, (0, 0, HEAD_Z), mat_body))
# Visor mắt — nằm phía trước (-Y), ngay tâm đầu
parts.append(add_box("Visor",
                      (0.18, 0.06, 0.16),
                      (0, -0.09, 1.66),
                      mat_accent))

# ── CỔ ───────────────────────────────────────────────────────────────────────
parts.append(add_cylinder("Neck",
                            0.045, 0.10,
                            (0, 0, 1.54),  # dọc Z
                            mat=mat_joint))

# ── THÂN ─────────────────────────────────────────────────────────────────────
# Upper Chest
parts.append(add_box("Torso_Upper",
                      (0.38, 0.24, 0.28),
                      (0, 0, 1.32),
                      mat_body))
# Lower Chest/Belly
parts.append(add_box("Torso_Lower",
                      (0.32, 0.20, 0.22),
                      (0, 0, 1.10),
                      mat_body))
# Waist cylinder (Cyan)
parts.append(add_cylinder("Waist",
                            0.07, 0.12,
                            (0, 0, 0.925),
                            mat=mat_joint))

# ── KHUNG CHẬU ───────────────────────────────────────────────────────────────
parts.append(add_box("Pelvis",
                      (0.32, 0.18, 0.12),
                      (0, 0, 0.79),
                      mat_joint))

# ── TAY — T-POSE (duỗi thẳng dọc trục X) ────────────────────────────────────
for side, sign in (("L", +1), ("R", -1)):
    # Khớp vai (Shoulder)
    parts.append(add_sphere(
        f"Shoulder_{side}",
        0.055,
        (sign * 0.25, 0, 1.35),
        mat_joint
    ))

    # Cánh tay trên (upper arm)
    parts.append(add_cylinder(
        f"UpperArm_{side}",
        0.04,             # bán kính
        0.24,             # chiều dài
        (sign * 0.40, 0, 1.35),
        rotation=(0, HALF_PI, 0),   # ← xoay để nằm ngang theo X
        mat=mat_body
    ))

    # Khuỷu tay (elbow joint)
    parts.append(add_sphere(
        f"Elbow_{side}",
        0.048,
        (sign * 0.58, 0, 1.35),
        mat_joint
    ))

    # Cánh tay dưới (forearm)
    parts.append(add_cylinder(
        f"LowerArm_{side}",
        0.035,
        0.22,
        (sign * 0.72, 0, 1.35),
        rotation=(0, HALF_PI, 0),
        mat=mat_joint
    ))

    # Bàn tay (Hand)
    parts.append(add_box(
        f"Hand_{side}",
        (0.06, 0.08, 0.016),
        (sign * 0.85, 0, 1.35),
        mat_accent
    ))

    # Ngón tay
    parts.append(add_cylinder(f"Finger1_{side}", 0.007, 0.05, (sign * 0.89, 0.02, 1.35), rotation=(0, HALF_PI, 0), mat=mat_body))
    parts.append(add_cylinder(f"Finger2_{side}", 0.007, 0.05, (sign * 0.89, 0.00, 1.35), rotation=(0, HALF_PI, 0), mat=mat_body))
    parts.append(add_cylinder(f"Finger3_{side}", 0.007, 0.05, (sign * 0.89, -0.02, 1.35), rotation=(0, HALF_PI, 0), mat=mat_body))
    parts.append(add_cylinder(f"Thumb_{side}", 0.007, 0.04, (sign * 0.85, 0.00, 1.31), mat=mat_body)) # vertical along Z

# ── CHÂN — thẳng đứng (dọc trục Z, không cần xoay) ──────────────────────────
for side, sign in (("L", +1), ("R", -1)):
    # Hông
    parts.append(add_sphere(f"HipJoint_{side}", 0.055, (sign * 0.12, 0, 0.70), mat_joint))

    # Đùi (upper leg)
    parts.append(add_cylinder(
        f"UpperLeg_{side}",
        0.05, 0.28,
        (sign * 0.12, 0, 0.51),
        mat=mat_body
    ))

    # Đầu gối (knee joint)
    parts.append(add_sphere(f"Knee_{side}", 0.048, (sign * 0.12, 0, 0.32), mat_joint))

    # Bắp chân (lower leg)
    parts.append(add_cylinder(
        f"LowerLeg_{side}",
        0.04, 0.28,
        (sign * 0.12, 0, 0.16),
        mat=mat_joint
    ))

    # Cổ chân
    parts.append(add_sphere(f"Ankle_{side}", 0.035, (sign * 0.12, 0, 0.00), mat_joint))

    # Bàn chân
    parts.append(add_box(
        f"Foot_{side}",
        (0.07, 0.16, 0.03),
        (sign * 0.12, 0.04, -0.04),
        mat_accent
    ))

# ────────────────────────────────────────────────────────────────────────────
# 4. GỘP MESH → tạo bản STATIC
# ────────────────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
for p in parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()

robot_mesh      = bpy.context.active_object
robot_mesh.name = "ROBA_Robot"

# Sao chép để export static (không gắn armature)
static_copy      = robot_mesh.copy()
static_copy.data = robot_mesh.data.copy()
static_copy.name = "ROBA_Robot_Static"
bpy.context.collection.objects.link(static_copy)

# ────────────────────────────────────────────────────────────────────────────
# 5. TẠO ARMATURE — khớp với tư thế chữ T
# ────────────────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
armature_obj      = bpy.context.active_object
armature_obj.name = "ROBA_Armature"
eb = armature_obj.data.edit_bones
eb.remove(eb[0])   # xoá bone mặc định


def add_bone(name, head, tail, parent=None, connect=False):
    """Tạo 1 bone; head/tail là tuple (x, y, z)."""
    b = eb.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent    = parent
        b.use_connect = connect
    return b


# ── Cột sống (trục Z, chạy từ khung chậu lên đầu) ──────────────────────────
root  = add_bone("root",  (0,0, PELVIS_Z),        (0,0, PELVIS_Z + 0.05))
spine = add_bone("spine", (0,0, PELVIS_Z),         (0,0, TORSO_Z),   root)
chest = add_bone("chest", (0,0, TORSO_Z),          (0,0, NECK_Z),    spine, True)
neck  = add_bone("neck",  (0,0, NECK_Z),           (0,0, NECK_Z + NECK_H), chest, True)
_head = add_bone("head",  (0,0, NECK_Z + NECK_H),  (0,0, HEAD_Z + HEAD_H * 0.55), neck, True)

# ── Tay — bone chạy ngang trục X (T-pose) ───────────────────────────────────
#
#   Với tư thế chữ T, tất cả các bone tay đều có head.z = tail.z = SHOULDER_Z
#   và chỉ thay đổi theo trục X (sign × chiều dài từng đoạn).
#
for side, sign in (("L", +1), ("R", -1)):
    shoulder_x = sign * SHOULDER_W / 2
    elbow_x    = shoulder_x + sign * UPPER_ARM_L
    wrist_x    = elbow_x   + sign * LOWER_ARM_L
    hand_tip_x = wrist_x   + sign * HAND_L

    # bone vai: từ cột sống ra đến khớp vai (chạy ngang X)
    clavicle  = add_bone(f"clavicle_{side}",
                          (0,           0, SHOULDER_Z),
                          (shoulder_x,  0, SHOULDER_Z),
                          chest)
    # bone cánh tay trên
    upper_arm = add_bone(f"upper_arm_{side}",
                          (shoulder_x, 0, SHOULDER_Z),
                          (elbow_x,    0, SHOULDER_Z),
                          clavicle, True)
    # bone cẳng tay
    lower_arm = add_bone(f"lower_arm_{side}",
                          (elbow_x, 0, SHOULDER_Z),
                          (wrist_x, 0, SHOULDER_Z),
                          upper_arm, True)
    # bone bàn tay
    add_bone(f"hand_{side}",
              (wrist_x,    0, SHOULDER_Z),
              (hand_tip_x, 0, SHOULDER_Z),
              lower_arm, True)

# ── Chân — bone chạy thẳng đứng (-Z) ────────────────────────────────────────
for side, sign in (("L", +1), ("R", -1)):
    hip_x   = sign * HIP_W / 2
    knee_z  = PELVIS_Z  - UPPER_LEG_L
    ankle_z = knee_z    - LOWER_LEG_L
    toe_z   = ankle_z   - LIMB_R * 0.5

    hip_bone  = add_bone(f"hip_{side}",
                          (hip_x, 0, PELVIS_Z),
                          (hip_x, 0, PELVIS_Z - 0.05),   # bone ngắn ở khớp háng
                          root)
    upper_leg = add_bone(f"upper_leg_{side}",
                          (hip_x, 0, PELVIS_Z),
                          (hip_x, 0, knee_z),
                          hip_bone, True)
    lower_leg = add_bone(f"lower_leg_{side}",
                          (hip_x, 0, knee_z),
                          (hip_x, 0, ankle_z),
                          upper_leg, True)
    add_bone(f"foot_{side}",
              (hip_x, 0,       ankle_z),
              (hip_x, FOOT_L,  toe_z),
              lower_leg, True)

bpy.ops.object.mode_set(mode="OBJECT")

# ────────────────────────────────────────────────────────────────────────────
# 6. GẮN MESH VÀO ARMATURE (Automatic Weights) → bản RIGGED
# ────────────────────────────────────────────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
robot_mesh.select_set(True)
armature_obj.select_set(True)
bpy.context.view_layer.objects.active = armature_obj
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

robot_mesh.name = "ROBA_Robot_Rigged_Mesh"

# ────────────────────────────────────────────────────────────────────────────
# 7. XUẤT FILE
# ────────────────────────────────────────────────────────────────────────────
out_dir = bpy.path.abspath("//") or os.getcwd()
print(f"[ROBA] Xuat file vao: {out_dir}")

# ── 7a. STATIC — chỉ mesh, không armature ────────────────────────────────────
bpy.ops.object.select_all(action="DESELECT")
static_copy.select_set(True)
bpy.context.view_layer.objects.active = static_copy

bpy.ops.export_scene.gltf(
    filepath=os.path.join(out_dir, "ROBA_static.glb"),
    use_selection=True, export_apply=True,
)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(out_dir, "ROBA_static.fbx"),
    use_selection=True, apply_unit_scale=True,
)

# ── 7b. RIGGED — armature + mesh đã skin, tư thế chữ T = rest pose ───────────
bpy.ops.object.select_all(action="DESELECT")
armature_obj.select_set(True)
robot_mesh.select_set(True)
bpy.context.view_layer.objects.active = armature_obj

bpy.ops.export_scene.gltf(
    filepath=os.path.join(out_dir, "ROBA_rigged.glb"),
    use_selection=True, export_apply=True,
)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(out_dir, "ROBA_rigged.fbx"),
    use_selection=True, add_leaf_bones=False, apply_unit_scale=True,
)

print("=== HOAN TAT ===")
print(f"  ROBA_static.glb/.fbx  (geometry tinh, khong armature)")
print(f"  ROBA_rigged.glb/.fbx  (co armature T-pose, skin weights)")
