import os
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial

def create_humanoid_robot():
    # Define standard colors
    # White Plastic (Armor)
    white_color = np.array([245, 245, 245, 255], dtype=np.uint8)
    # Dark Grey Metallic (Skeleton/Chassis)
    grey_color = np.array([45, 45, 48, 255], dtype=np.uint8)
    # Cyan Glowing Light (Energy core / Visor)
    cyan_color = np.array([0, 220, 255, 255], dtype=np.uint8)

    parts = []

    # Helper function to set mesh color
    def paint_mesh(mesh, rgba):
        mesh.visual.face_colors = rgba
        return mesh

    # 1. TORSO (BODY)
    # Chest
    chest = trimesh.creation.box(extents=[0.4, 0.25, 0.5])
    chest.apply_translation([0, 0, 1.25])
    parts.append(paint_mesh(chest, white_color))

    # Core Plate (Cyan glowing core in the middle of the chest)
    core_plate = trimesh.creation.box(extents=[0.18, 0.03, 0.18])
    core_plate.apply_translation([0, -0.13, 1.25])
    parts.append(paint_mesh(core_plate, cyan_color))

    # Waist/Spine (Robotic joint)
    spine = trimesh.creation.cylinder(radius=0.08, height=0.15)
    spine.apply_translation([0, 0, 0.925])
    parts.append(paint_mesh(spine, grey_color))

    # Pelvis/Hip base
    pelvis = trimesh.creation.box(extents=[0.32, 0.2, 0.12])
    pelvis.apply_translation([0, 0, 0.79])
    parts.append(paint_mesh(pelvis, white_color))

    # 2. HEAD
    # Neck
    neck = trimesh.creation.cylinder(radius=0.05, height=0.08)
    neck.apply_translation([0, 0, 1.54])
    parts.append(paint_mesh(neck, grey_color))

    # Head sphere (Stylized spherical head)
    head = trimesh.creation.icosphere(subdivisions=3, radius=0.15)
    head.apply_translation([0, 0, 1.68])
    parts.append(paint_mesh(head, white_color))

    # Visor (Robot glowing eyes/visor)
    visor = trimesh.creation.box(extents=[0.2, 0.05, 0.06])
    visor.apply_translation([0, -0.13, 1.7])
    parts.append(paint_mesh(visor, cyan_color))

    # Ears/Antenna bases (Cylinders on sides of head)
    rot_y = trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]) # Rotate to face sides
    rot_x = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])
    
    left_ear = trimesh.creation.cylinder(radius=0.02, height=0.05)
    left_ear.apply_transform(rot_x)
    left_ear.apply_translation([0.16, 0, 1.68])
    parts.append(paint_mesh(left_ear, grey_color))

    right_ear = trimesh.creation.cylinder(radius=0.02, height=0.05)
    right_ear.apply_transform(rot_x)
    right_ear.apply_translation([-0.16, 0, 1.68])
    parts.append(paint_mesh(right_ear, grey_color))

    # 3. ARMS (Left & Right - Dang ngang in T-Pose)
    # Note: cylinders are naturally aligned with Z-axis, so we rotate them to align with X-axis.
    rot_z_to_x = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])

    # Left Shoulder Joint
    l_shoulder = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
    l_shoulder.apply_translation([0.25, 0, 1.35])
    parts.append(paint_mesh(l_shoulder, grey_color))

    # Left Upper Arm
    l_up_arm = trimesh.creation.cylinder(radius=0.045, height=0.25)
    l_up_arm.apply_transform(rot_z_to_x)
    l_up_arm.apply_translation([0.425, 0, 1.35])
    parts.append(paint_mesh(l_up_arm, white_color))

    # Left Elbow Joint
    l_elbow = trimesh.creation.icosphere(subdivisions=2, radius=0.05)
    l_elbow.apply_translation([0.58, 0, 1.35])
    parts.append(paint_mesh(l_elbow, grey_color))

    # Left Forearm
    l_forearm = trimesh.creation.cylinder(radius=0.038, height=0.22)
    l_forearm.apply_transform(rot_z_to_x)
    l_forearm.apply_translation([0.72, 0, 1.35])
    parts.append(paint_mesh(l_forearm, white_color))

    # Left Hand (Paddle/Claw style)
    l_hand = trimesh.creation.box(extents=[0.06, 0.06, 0.02])
    l_hand.apply_translation([0.85, 0, 1.35])
    parts.append(paint_mesh(l_hand, grey_color))

    # Right Shoulder Joint
    r_shoulder = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
    r_shoulder.apply_translation([-0.25, 0, 1.35])
    parts.append(paint_mesh(r_shoulder, grey_color))

    # Right Upper Arm
    r_up_arm = trimesh.creation.cylinder(radius=0.045, height=0.25)
    r_up_arm.apply_transform(rot_z_to_x)
    r_up_arm.apply_translation([-0.425, 0, 1.35])
    parts.append(paint_mesh(r_up_arm, white_color))

    # Right Elbow Joint
    r_elbow = trimesh.creation.icosphere(subdivisions=2, radius=0.05)
    r_elbow.apply_translation([-0.58, 0, 1.35])
    parts.append(paint_mesh(r_elbow, grey_color))

    # Right Forearm
    r_forearm = trimesh.creation.cylinder(radius=0.038, height=0.22)
    r_forearm.apply_transform(rot_z_to_x)
    r_forearm.apply_translation([-0.72, 0, 1.35])
    parts.append(paint_mesh(r_forearm, white_color))

    # Right Hand
    r_hand = trimesh.creation.box(extents=[0.06, 0.06, 0.02])
    r_hand.apply_translation([-0.85, 0, 1.35])
    parts.append(paint_mesh(r_hand, grey_color))

    # 4. LEGS (Left & Right - Vertical placement)
    # Left Hip Joint
    l_hip = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
    l_hip.apply_translation([0.12, 0, 0.70])
    parts.append(paint_mesh(l_hip, grey_color))

    # Left Thigh
    l_thigh = trimesh.creation.cylinder(radius=0.055, height=0.3)
    l_thigh.apply_translation([0.12, 0, 0.50])
    parts.append(paint_mesh(l_thigh, white_color))

    # Left Knee Joint
    l_knee = trimesh.creation.icosphere(subdivisions=2, radius=0.05)
    l_knee.apply_translation([0.12, 0, 0.32])
    parts.append(paint_mesh(l_knee, grey_color))

    # Left Calf
    l_calf = trimesh.creation.cylinder(radius=0.045, height=0.32)
    l_calf.apply_translation([0.12, 0, 0.12])
    parts.append(paint_mesh(l_calf, white_color))

    # Left Foot (Flat box)
    l_foot = trimesh.creation.box(extents=[0.08, 0.16, 0.04])
    l_foot.apply_translation([0.12, -0.04, -0.06])
    parts.append(paint_mesh(l_foot, grey_color))

    # Right Hip Joint
    r_hip = trimesh.creation.icosphere(subdivisions=2, radius=0.06)
    r_hip.apply_translation([-0.12, 0, 0.70])
    parts.append(paint_mesh(r_hip, grey_color))

    # Right Thigh
    r_thigh = trimesh.creation.cylinder(radius=0.055, height=0.3)
    r_thigh.apply_translation([-0.12, 0, 0.50])
    parts.append(paint_mesh(r_thigh, white_color))

    # Right Knee Joint
    r_knee = trimesh.creation.icosphere(subdivisions=2, radius=0.05)
    r_knee.apply_translation([-0.12, 0, 0.32])
    parts.append(paint_mesh(r_knee, grey_color))

    # Right Calf
    r_calf = trimesh.creation.cylinder(radius=0.045, height=0.32)
    r_calf.apply_translation([-0.12, 0, 0.12])
    parts.append(paint_mesh(r_calf, white_color))

    # Right Foot
    r_foot = trimesh.creation.box(extents=[0.08, 0.16, 0.04])
    r_foot.apply_translation([-0.12, -0.04, -0.06])
    parts.append(paint_mesh(r_foot, grey_color))

    # Combine all meshes into a single scene or combined mesh
    # Combining is cleaner for a single GLB asset
    combined_mesh = trimesh.util.concatenate(parts)
    return combined_mesh

if __name__ == '__main__':
    print("Generating ROBA humanoid robot in T-pose...")
    robot = create_humanoid_robot()
    
    # Ensure export directory exists
    output_dir = r"e:\Web3\ROBA\roba-robot-tpose"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "index.glb")
    
    # Export as GLB
    robot.export(output_path, file_type='glb')
    print(f"Robot successfully exported to: {output_path}")
