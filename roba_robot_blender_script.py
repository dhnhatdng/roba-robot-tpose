"""
ROBA Creator Hub — Robot T-Pose Generator
==========================================
Script chạy bên trong Blender (Scripting tab hoặc CLI headless).

Cách dùng:
  1. Mở Blender > tab "Scripting" > New > dán toàn bộ nội dung file này > Run Script.
     HOẶC chạy từ terminal (headless, không cần GUI):
       blender --background --python roba_robot_blender_script.py

  2. Kết quả: 2 file export trong cùng thư mục với file .blend (hoặc thư mục hiện hành
     khi chạy headless):
       - ROBA_Robot_Static.glb   -> hình học tĩnh, không có armature (static asset)
       - ROBA_Robot_Static.fbx
       - ROBA_Robot_Rigged.glb   -> có armature + skin weights, đứng tư thế chữ T (rigged/dynamic asset)
       - ROBA_Robot_Rigged.fbx

Thiết kế: low-poly, khối hình học cơ bản (capsule/cube/cylinder), tỉ lệ humanoid
chuẩn 7-8 đầu, tư thế chữ T gọn gàng (tay duỗi ngang vai, lòng bàn tay úp xuống,
chân khép, đầu nhìn thẳng) — phù hợp làm khung sườn (base mesh) để rig hoặc
dùng làm placeholder asset trong simulator.
"""

import bpy
import bmesh
import math
import os

# ---------------------------------------------------------------------------
# 0. DỌN SCENE
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials):
    for item in list(block):
        if item.users == 0:
            block.remove(item)

# ---------------------------------------------------------------------------
# 1. THÔNG SỐ TỈ LỆ (đơn vị: mét) — humanoid cao ~1.7m, 7.5 đầu
# ---------------------------------------------------------------------------
TOTAL_HEIGHT   = 1.70
HEAD_H         = TOTAL_HEIGHT / 7.5
NECK_H         = HEAD_H * 0.25
TORSO_H        = HEAD_H * 2.6
PELVIS_H       = HEAD_H * 0.9
UPPER_ARM_L    = HEAD_H * 1.6
LOWER_ARM_L    = HEAD_H * 1.4
HAND_L         = HEAD_H * 0.7
UPPER_LEG_L    = HEAD_H * 2.0
LOWER_LEG_L    = HEAD_H * 1.9
FOOT_L         = HEAD_H * 0.9

SHOULDER_W     = HEAD_H * 1.9   # khoảng cách 2 vai
HIP_W          = HEAD_H * 1.1
LIMB_R         = HEAD_H * 0.22  # bán kính chi (tay/chân) hình trụ

GROUND_Z       = 0.0
PELVIS_Z       = GROUND_Z + UPPER_LEG_L + LOWER_LEG_L + FOOT_L * 0.3
TORSO_Z        = PELVIS_Z + PELVIS_H
NECK_Z         = TORSO_Z + TORSO_H
HEAD_Z         = NECK_Z + NECK_H + HEAD_H / 2

ROBA_BLUE   = (0.10, 0.45, 0.95, 1.0)
ROBA_GREY   = (0.55, 0.58, 0.62, 1.0)
ROBA_ACCENT = (0.95, 0.65, 0.10, 1.0)


def make_material(name, rgba):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = rgba
        bsdf.inputs["Roughness"].default_value = 0.4
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.3
    return mat


mat_body   = make_material("ROBA_Body",   ROBA_BLUE)
mat_joint  = make_material("ROBA_Joint",  ROBA_GREY)
mat_accent = make_material("ROBA_Accent", ROBA_ACCENT)


def add_box(name, size, location, material=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    if material:
        obj.data.materials.append(material)
    return obj


def add_cylinder(name, radius, depth, location, rotation=(0, 0, 0), material=None):
    bpy.ops.mesh.primitive_cylinder_add(
        radius=radius, depth=depth, location=location,
        rotation=rotation, vertices=12
    )
    obj = bpy.context.active_object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    return obj


def add_sphere(name, radius, location, material=None):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location, segments=16, ring_count=10
    )
    obj = bpy.context.active_object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    return obj


# ---------------------------------------------------------------------------
# 2. DỰNG HÌNH HỌC (mesh primitives) — tư thế chữ T
# ---------------------------------------------------------------------------
parts = []

# --- Đầu ---
parts.append(add_sphere("Head", HEAD_H * 0.5, (0, 0, HEAD_Z), mat_body))
parts.append(add_box("Visor",
                      (HEAD_H * 0.55, HEAD_H * 0.15, HEAD_H * 0.25),
                      (0, -HEAD_H * 0.42, HEAD_Z), mat_accent))

# --- Cổ ---
parts.append(add_cylinder("Neck", LIMB_R * 0.8, NECK_H,
                            (0, 0, NECK_Z + NECK_H / 2), material=mat_joint))

# --- Thân ---
parts.append(add_box("Torso",
                      (SHOULDER_W * 0.85, HEAD_H * 0.9, TORSO_H),
                      (0, 0, TORSO_Z + TORSO_H / 2), mat_body))

# --- Khung chậu ---
parts.append(add_box("Pelvis",
                      (HIP_W * 1.4, HEAD_H * 0.85, PELVIS_H),
                      (0, 0, PELVIS_Z + PELVIS_H / 2), mat_joint))

# --- Tay (T-pose: duỗi ngang theo trục X, song song mặt đất) ---
for side, sign in (("L", 1), ("R", -1)):
    shoulder_x = sign * SHOULDER_W / 2
    shoulder_z = TORSO_Z + TORSO_H * 0.92

    upper_arm_cx = shoulder_x + sign * UPPER_ARM_L / 2
    parts.append(add_cylinder(
        f"UpperArm_{side}", LIMB_R, UPPER_ARM_L,
        (upper_arm_cx, 0, shoulder_z),
        rotation=(0, math.radians(90), 0), material=mat_body))

    elbow_x = shoulder_x + sign * UPPER_ARM_L
    lower_arm_cx = elbow_x + sign * LOWER_ARM_L / 2
    parts.append(add_cylinder(
        f"LowerArm_{side}", LIMB_R * 0.85, LOWER_ARM_L,
        (lower_arm_cx, 0, shoulder_z),
        rotation=(0, math.radians(90), 0), material=mat_joint))

    wrist_x = elbow_x + sign * LOWER_ARM_L
    hand_cx = wrist_x + sign * HAND_L / 2
    parts.append(add_box(
        f"Hand_{side}",
        (HAND_L, LIMB_R * 1.6, LIMB_R * 1.2),
        (hand_cx, 0, shoulder_z), mat_accent))

# --- Chân (thẳng đứng, khép, đứng tự nhiên) ---
for side, sign in (("L", 1), ("R", -1)):
    hip_x = sign * HIP_W / 2
    upper_leg_cz = PELVIS_Z - UPPER_LEG_L / 2
    parts.append(add_cylinder(
        f"UpperLeg_{side}", LIMB_R * 1.1, UPPER_LEG_L,
        (hip_x, 0, upper_leg_cz), material=mat_body))

    knee_z = PELVIS_Z - UPPER_LEG_L
    lower_leg_cz = knee_z - LOWER_LEG_L / 2
    parts.append(add_cylinder(
        f"LowerLeg_{side}", LIMB_R * 0.95, LOWER_LEG_L,
        (hip_x, 0, lower_leg_cz), material=mat_joint))

    ankle_z = knee_z - LOWER_LEG_L
    parts.append(add_box(
        f"Foot_{side}",
        (LIMB_R * 2.0, FOOT_L, LIMB_R * 1.0),
        (hip_x, FOOT_L * 0.2, ankle_z - LIMB_R * 0.5), mat_accent))

# ---------------------------------------------------------------------------
# 3. GỘP MESH (cho bản STATIC) — giữ bản sao trước khi rig
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
for p in parts:
    p.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
robot_mesh = bpy.context.active_object
robot_mesh.name = "ROBA_Robot"

# Bản sao riêng cho static export (không dính armature)
static_copy = robot_mesh.copy()
static_copy.data = robot_mesh.data.copy()
static_copy.name = "ROBA_Robot_Static"
bpy.context.collection.objects.link(static_copy)

# ---------------------------------------------------------------------------
# 4. TẠO ARMATURE (khung xương) khớp với tư thế chữ T
# ---------------------------------------------------------------------------
bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
armature_obj = bpy.context.active_object
armature_obj.name = "ROBA_Armature"
eb = armature_obj.data.edit_bones
eb.remove(eb[0])   # xóa bone mặc định

def add_bone(name, head, tail, parent=None, connect=False):
    b = eb.new(name)
    b.head = head
    b.tail = tail
    if parent:
        b.parent = parent
        b.use_connect = connect
    return b

root  = add_bone("root",  (0, 0, PELVIS_Z), (0, 0, PELVIS_Z + 0.05))
spine = add_bone("spine", (0, 0, PELVIS_Z), (0, 0, TORSO_Z), root)
chest = add_bone("chest", (0, 0, TORSO_Z),  (0, 0, NECK_Z),  spine, True)
neck  = add_bone("neck",  (0, 0, NECK_Z),   (0, 0, NECK_Z + NECK_H), chest, True)
head  = add_bone("head",  (0, 0, NECK_Z + NECK_H), (0, 0, HEAD_Z + HEAD_H * 0.5), neck, True)

for side, sign in (("L", 1), ("R", -1)):
    shoulder_x = sign * SHOULDER_W / 2
    shoulder_z = TORSO_Z + TORSO_H * 0.92
    elbow_x    = shoulder_x + sign * UPPER_ARM_L
    wrist_x    = elbow_x   + sign * LOWER_ARM_L
    hand_x     = wrist_x   + sign * HAND_L

    shoulder  = add_bone(f"shoulder_{side}",  (0, 0, shoulder_z),      (shoulder_x, 0, shoulder_z), chest)
    upper_arm = add_bone(f"upper_arm_{side}",  (shoulder_x, 0, shoulder_z), (elbow_x, 0, shoulder_z), shoulder, True)
    lower_arm = add_bone(f"lower_arm_{side}",  (elbow_x, 0, shoulder_z),    (wrist_x, 0, shoulder_z), upper_arm, True)
    add_bone(f"hand_{side}",   (wrist_x, 0, shoulder_z), (hand_x, 0, shoulder_z), lower_arm, True)

    hip_x   = sign * HIP_W / 2
    knee_z  = PELVIS_Z - UPPER_LEG_L
    ankle_z = knee_z   - LOWER_LEG_L

    hip = add_bone(f"hip_{side}", (hip_x, 0, PELVIS_Z), (hip_x, 0, PELVIS_Z), root)
    upper_leg = add_bone(f"upper_leg_{side}", (hip_x, 0, PELVIS_Z), (hip_x, 0, knee_z),  hip,       True)
    lower_leg = add_bone(f"lower_leg_{side}", (hip_x, 0, knee_z),   (hip_x, 0, ankle_z), upper_leg, True)
    add_bone(f"foot_{side}", (hip_x, 0, ankle_z), (hip_x, FOOT_L, ankle_z - LIMB_R), lower_leg, True)

bpy.ops.object.mode_set(mode="OBJECT")

# ---------------------------------------------------------------------------
# 5. GẮN MESH VÀO ARMATURE (Automatic Weights) -> bản RIGGED
# ---------------------------------------------------------------------------
bpy.ops.object.select_all(action="DESELECT")
robot_mesh.select_set(True)
armature_obj.select_set(True)
bpy.context.view_layer.objects.active = armature_obj
bpy.ops.object.parent_set(type="ARMATURE_AUTO")

robot_mesh.name = "ROBA_Robot_Rigged_Mesh"

# ---------------------------------------------------------------------------
# 6. XUẤT FILE
# ---------------------------------------------------------------------------
out_dir = bpy.path.abspath("//") or os.getcwd()

# --- 6a. STATIC (chỉ mesh, không armature) ---
bpy.ops.object.select_all(action="DESELECT")
static_copy.select_set(True)
bpy.context.view_layer.objects.active = static_copy

bpy.ops.export_scene.gltf(
    filepath=os.path.join(out_dir, "ROBA_Robot_Static.glb"),
    use_selection=True, export_apply=True,
)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(out_dir, "ROBA_Robot_Static.fbx"),
    use_selection=True, apply_unit_scale=True,
)

# --- 6b. RIGGED (armature + mesh đã skin, vẫn ở tư thế chữ T = rest pose) ---
bpy.ops.object.select_all(action="DESELECT")
armature_obj.select_set(True)
robot_mesh.select_set(True)
bpy.context.view_layer.objects.active = armature_obj

bpy.ops.export_scene.gltf(
    filepath=os.path.join(out_dir, "ROBA_Robot_Rigged.glb"),
    use_selection=True, export_apply=True,
)
bpy.ops.export_scene.fbx(
    filepath=os.path.join(out_dir, "ROBA_Robot_Rigged.fbx"),
    use_selection=True, add_leaf_bones=False, apply_unit_scale=True,
)

print("=== HOÀN TẤT ===")
print(f"Xuất file vào: {out_dir}")
print(" - ROBA_Robot_Static.glb / .fbx   (asset tĩnh)")
print(" - ROBA_Robot_Rigged.glb / .fbx   (asset có khớp nối, tư thế chữ T)")
