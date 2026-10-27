# -*- coding: utf-8 -*-
# VERSION 2.3
"""
KeyShot 八视图批量渲染 v2.3（在 KeyShot 的脚本窗口中运行）。

默认输出：当前已保存 BIP 场景所在文件夹/当前可见模型组名称+八视图。
多个模型组同时可见时，用“+”连接名称，例如“模型A+模型B八视图”。
无法确定场景完整路径时弹出目录选择框，不再静默转存到桌面或资源目录。
只读取可见零件的世界坐标包围盒；隐藏的父组、模型和未激活模型集均排除。
不移动、不删除、不显示/隐藏任何模型，不保存或覆盖 BIP 场景。
运行信息仅显示在脚本控制台，不生成日志文件。

取景算法已用 KeyShot 11.1 验证：正交画面宽度 =
2 * camera_distance * tan(horizontal_fov / 2)。
逐零件投影包围盒，按输出宽高比留边；不调用场景根节点 centerAndFit()。
"""
from __future__ import print_function

import math
import os
import re
import time
import traceback

import lux


# 留空：自动寻找当前场景目录。填写时必须是绝对路径，直接作为输出目录。
OUTPUT_DIR_OVERRIDE = r""
FILE_PREFIX_OVERRIDE = r""
OUTPUT_EXT = "png"
NUMBERED_FILENAMES = True
RENDER_WIDTH_OVERRIDE = 2560
RENDER_HEIGHT_OVERRIDE = 1599

# 模型包围范围占画面的比例；0.85 为约 85%，调大则模型更大。
# 包围盒会略大于真实轮廓，尤其是斜视图。建议 0.80～0.90。
FRAME_FILL_RATIO = 0.85

# 仅作用于脚本工作相机；固定视场角使不同电脑的取景计算一致。
WORK_CAMERA_FOV = 30.0
WORK_CAMERA_NAME = "__batch_8_views2_camera__"
SAVE_CAMERA_BEFORE_RENDER = True
OPEN_OUTPUT_FOLDER_WHEN_DONE = True

UP_45_AZIMUTH = 45.0
UP_45_INCLINATION = 45.0
DOWN_45_AZIMUTH = 45.0
DOWN_45_INCLINATION = -45.0
VIEW_DEFS = [
    ("front", None, None), ("back", None, None),
    ("left", None, None), ("right", None, None),
    ("top", None, None), ("bottom", None, None),
    ("up45", UP_45_AZIMUTH, UP_45_INCLINATION),
    ("down45", DOWN_45_AZIMUTH, DOWN_45_INCLINATION),
]
EXT_TO_FORMAT_CONST = {
    "png": "RENDER_OUTPUT_PNG",
    "jpg": "RENDER_OUTPUT_JPEG", "jpeg": "RENDER_OUTPUT_JPEG",
    "tif": "RENDER_OUTPUT_TIFF8", "tiff": "RENDER_OUTPUT_TIFF8",
    "exr": "RENDER_OUTPUT_EXR", "psd": "RENDER_OUTPUT_PSD8",
}


class Cancelled(Exception):
    pass


def log(message):
    line = "[8views2] {0}".format(message)
    print(line)


def message_box(message, error=False):
    if hasattr(lux, "isHeadless") and lux.isHeadless():
        return
    try:
        lux.getMessageBox(
            msg=message, title="KeyShot 八视图 v2.3",
            type=lux.MESSAGE_BOX_CRITICAL if error else lux.MESSAGE_BOX_INFO)
    except Exception:
        print(message)


def normalized_info(info):
    # KeyShot 11.1 实际字段是 file、name、render_width、render_height；
    # 同时兼容其他版本的空格、下划线及大小写差异。
    return {re.sub(r"[\s_-]+", "", str(k)).lower(): v
            for k, v in info.items()}


def clean_path(value):
    if not isinstance(value, str):
        return ""
    return os.path.normpath(os.path.expanduser(os.path.expandvars(
        value.strip().strip('"')))) if value.strip() else ""


def absolute_path(value):
    path = clean_path(value)
    if not path or not os.path.isabs(path):
        return ""
    # Windows 的 \folder 和 C:folder 都不能独立确定完整位置。
    if os.name == "nt" and not os.path.splitdrive(path)[0]:
        return ""
    return path


def resolve_scene_file(info):
    data = normalized_info(info)
    keys = ("file", "filename", "filepath", "scenefile", "scenepath",
            "fullpath", "path", "name")
    # 检查所有候选项，不能让只有文件名的字段盖过后面的完整路径。
    for key in keys:
        path = absolute_path(data.get(key))
        if path and path.lower().endswith((".bip", ".ksp")) and os.path.isfile(path):
            return path
    for folder_key in ("directory", "folder", "filedirectory", "scenedirectory"):
        folder = absolute_path(data.get(folder_key))
        if folder and os.path.isdir(folder):
            for key in ("file", "filename", "name"):
                name = clean_path(data.get(key))
                if name and name == os.path.basename(name):
                    path = os.path.join(folder, name)
                    if path.lower().endswith((".bip", ".ksp")) and os.path.isfile(path):
                        return path
    return ""


def safe_name(value, fallback="keyshot"):
    name = os.path.basename(str(value or fallback))
    if name.lower().endswith((".bip", ".ksp")):
        name = os.path.splitext(name)[0]
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name).strip(" .")
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I):
        name = "_" + name
    return name or fallback


def model_folder_name(model_names):
    # 模型组名不是文件路径；替换非法字符，保留名称的各个部分。
    name = "+".join(model_names) or "当前模型"
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]+', "_", name).strip(" .")
    return (name or "当前模型") + "八视图"


def get_output_dir(info, scene_file, folder_name="当前模型八视图"):
    if OUTPUT_DIR_OVERRIDE.strip():
        path = absolute_path(OUTPUT_DIR_OVERRIDE)
        if not path:
            raise RuntimeError("OUTPUT_DIR_OVERRIDE 必须填写完整绝对路径。")
    elif scene_file:
        path = os.path.join(os.path.dirname(scene_file), folder_name)
    else:
        log("无法确定当前场景的完整路径；场景信息：{0!r}".format(info))
        if hasattr(lux, "isHeadless") and lux.isHeadless():
            raise RuntimeError("无法确定场景目录。请填写 OUTPUT_DIR_OVERRIDE。")
        folder = lux.getInputFolder(
            title="无法取得场景完整路径：请选择场景所在文件夹（将在其中建立“{0}”）".format(folder_name))
        if not folder:
            raise Cancelled("已取消选择输出位置，未开始渲染。")
        folder = absolute_path(folder)
        if not folder or not os.path.isdir(folder):
            raise RuntimeError("所选目录不存在，或不是绝对路径。")
        path = os.path.join(folder, folder_name)
    if not os.path.isdir(path):
        os.makedirs(path)
    return path


def get_render_size(info):
    if bool(RENDER_WIDTH_OVERRIDE) != bool(RENDER_HEIGHT_OVERRIDE):
        raise RuntimeError("宽和高需要同时填写，或同时设为 0。")
    if RENDER_WIDTH_OVERRIDE and RENDER_HEIGHT_OVERRIDE:
        size = int(RENDER_WIDTH_OVERRIDE), int(RENDER_HEIGHT_OVERRIDE)
    else:
        data = normalized_info(info)
        size = (int(data.get("renderwidth") or data.get("renderingwidth") or 0),
                int(data.get("renderheight") or data.get("renderingheight") or 0))
    if min(size) <= 0:
        raise RuntimeError("无法取得输出尺寸，请设置脚本顶部的宽和高。")
    return size


def vector3(value):
    # luxmath.Vector 不支持迭代，需调用 val()；相机函数则返回 tuple。
    if hasattr(value, "val"):
        value = value.val()
    values = tuple(float(value[i]) for i in range(3))
    if not all(math.isfinite(v) for v in values):
        raise RuntimeError("模型或相机坐标包含无效数值。")
    return values


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1]*b[2] - a[2]*b[1],
            a[2]*b[0] - a[0]*b[2],
            a[0]*b[1] - a[1]*b[0])


def normalize(v):
    length = math.sqrt(dot(v, v))
    if length < 1e-15:
        raise RuntimeError("相机方向无效，无法计算取景。")
    return tuple(x / length for x in v)


def visible_bounds(model_names=None):
    """读取可见几何叶节点，兼容以 GROUP 暴露的 CAD 曲面实体。"""
    try:
        root = lux.getSceneTree()
    except Exception as exc:
        raise RuntimeError("没有可用的场景树。请打开场景并激活需要渲染的模型集。\n{0}".format(exc))
    # 部分 CAD/NURBS 文件把实体暴露为 GROUP 叶节点，isObject() 为
    # False，甚至 find(types=OBJECT) 也返回空。其 ID 仍存在于
    # getObjects() 中，可据此识别真实几何，避免把空分组当成模型。
    geometry_ids = set(lux.getObjects())
    bounds = []
    ignored = [0]
    seen = set()

    def walk(node, model_name=None):
        key = (node.getKind(), node.getID())
        if key in seen:
            return
        seen.add(key)
        # 未激活模型集在场景树中也标记为 hidden；不按显示名称匹配。
        # 隐藏父组时直接停止遍历，后代自身的隐藏标记不影响此判断。
        if node.isHidden():
            ignored[0] += 1
            return
        if node.isAnimation():
            return
        # 沿当前可见分支保留顶层模型组名称，只有实际贡献几何时才记录。
        # 不取 BIP 文件名，也不取“Default”等模型集名称。
        if node.isModel() or (model_name is None and not node.isModelSet()):
            model_name = node.getName().strip() or model_name
        is_object = node.isObject()
        children = [] if is_object else list(node.getChildren())
        if children:
            for child in children:
                walk(child, model_name)
            return
        if not is_object and (node.isModelSet() or node.getID() not in geometry_ids):
            return
        low, high = node.getBoundingBox(world=True)
        low, high = vector3(low), vector3(high)
        if any(low[i] > high[i] for i in range(3)):
            raise RuntimeError("零件 {0} 的包围盒无效。".format(node.getName()))
        if max(high[i] - low[i] for i in range(3)) <= 1e-12:
            return
        bounds.append((low, high))
        if model_names is not None and model_name and model_name not in model_names:
            model_names.append(model_name)
    for child in root.getChildren():
        walk(child)
    if not bounds:
        raise RuntimeError("当前没有可见零件（场景包含 {0} 个几何对象，检查 {1} 个场景节点）。"
                           "请显示需要渲染的模型后再运行。".format(len(geometry_ids), len(seen)))
    log("参与取景的可见几何零件：{0}；排除的隐藏分支：{1}".format(len(bounds), ignored[0]))
    return bounds


def projected_bounds(bounds, right, up, forward):
    """逐零件投影，避免先合并世界包围盒而增大斜视图留白。"""
    lows = [float("inf")] * 3
    highs = [float("-inf")] * 3
    axes = (right, up, forward)
    for low, high in bounds:
        center = tuple((low[i] + high[i]) * 0.5 for i in range(3))
        half = tuple((high[i] - low[i]) * 0.5 for i in range(3))
        for j, axis in enumerate(axes):
            middle = dot(center, axis)
            radius = sum(abs(axis[i]) * half[i] for i in range(3))
            lows[j] = min(lows[j], middle - radius)
            highs[j] = max(highs[j], middle + radius)
    return lows, highs


def fit_visible(bounds, width, height):
    forward = normalize(vector3(lux.getCameraDirection()))
    right = normalize(cross(forward, vector3(lux.getCameraUp())))
    up = normalize(cross(right, forward))
    low, high = projected_bounds(bounds, right, up, forward)
    span_x, span_y = high[0] - low[0], high[1] - low[1]
    frame_width = max(span_x, span_y * float(width) / height) / FRAME_FILL_RATIO
    if frame_width <= 1e-12:
        raise RuntimeError("当前视角下可见模型没有有效尺寸。")
    fov = float(lux.getCameraFieldOfView())
    if not 0.01 < fov < 179.0:
        raise RuntimeError("无法取得有效的相机视场角。")
    distance = frame_width / (2.0 * math.tan(math.radians(fov) * 0.5))
    middle = [(low[i] + high[i]) * 0.5 for i in range(3)]
    # 对非常深的模型，将观察点沿视线前移以免相机进入几何体。
    # 正交投影下沿视线移动观察点不改变屏幕上的居中或比例。
    middle[2] = min(middle[2], low[2] + distance * 0.5)
    center = tuple(right[i]*middle[0] + up[i]*middle[1] + forward[i]*middle[2]
                   for i in range(3))
    angles = lux.getSphericalCamera()
    lux.setCameraLookAt(pt=center)
    lux.setSphericalCamera(*angles)
    lux.setCameraDistance(distance)
    lux.sync()
    log("可见范围 {0:.6g} x {1:.6g}；相机距离 {2:.6g}".format(
        span_x, span_y, distance))


def make_work_camera():
    old_name = lux.getCamera()
    names = set(lux.getCameras())
    # 如果用户当前就在脚本相机上，用另一个名称，避免改写当前相机。
    name = WORK_CAMERA_NAME if old_name != WORK_CAMERA_NAME else WORK_CAMERA_NAME + "_work"
    if name in names:
        lux.setCamera(name)
    else:
        result = lux.newCamera(name, False)
        if result is False:
            raise RuntimeError("无法建立工作相机。")
    if lux.getCamera() != name:
        raise RuntimeError("无法切换到工作相机；请检查相机是否锁定。")
    return name


def apply_view(label, azimuth, inclination, bounds, width, height):
    lux.setCameraPerspective()
    lux.setCameraFieldOfView(WORK_CAMERA_FOV)
    if azimuth is None:
        lux.setStandardView(getattr(lux, "VIEW_" + label.upper()))
    else:
        lux.setSphericalCamera(float(azimuth), float(inclination), 0.0)
    lux.setCameraOrthographic()
    lux.sync()
    fit_visible(bounds, width, height)
    if SAVE_CAMERA_BEFORE_RENDER:
        lux.saveCamera()
    lux.sync()


def get_render_options():
    opts = lux.getRenderOptions()
    # 防止继承渲染窗口的网络、后台或队列设置，导致图片不在本地，
    # 或尚未渲染就被旧脚本误报“完成”。质量、采样、透明背景保持原设置。
    opts.setAddToQueue(False)
    opts.setBackgroundRendering(False)
    opts.setSendToNetwork(False)
    opts.setRegion(None)
    return opts


def filename_for(base, index, label, ext):
    number = "{0:02d}_".format(index) if NUMBERED_FILENAMES else ""
    return "{0}_{1}{2}.{3}".format(base, number, label, ext)


def select_run_folder(folder, filenames):
    # 如已有同名图片，则整组另建子目录，避免覆盖旧图或将旧文件误报成功。
    if not any(os.path.exists(os.path.join(folder, name)) for name in filenames):
        return folder
    base = os.path.join(folder, time.strftime("run_%Y%m%d_%H%M%S"))
    path = base
    counter = 1
    while os.path.exists(path):
        path = base + "_{0}".format(counter)
        counter += 1
    os.makedirs(path)
    return path


def main():
    if not 0.1 <= FRAME_FILL_RATIO <= 0.98:
        raise RuntimeError("FRAME_FILL_RATIO 请设置在 0.1～0.98 之间。")
    info = lux.getSceneInfo() or {}
    scene_file = resolve_scene_file(info)
    data = normalized_info(info)
    base = safe_name(FILE_PREFIX_OVERRIDE.strip() or scene_file or
                     data.get("name") or data.get("file") or "keyshot")
    ext = OUTPUT_EXT.lower().lstrip(".")
    if ext not in EXT_TO_FORMAT_CONST:
        raise RuntimeError("不支持的输出格式：{0}".format(ext))
    width, height = get_render_size(info)
    lux.sync()
    model_names = []
    bounds = visible_bounds(model_names)
    out_dir = get_output_dir(info, scene_file, model_folder_name(model_names))
    filenames = [filename_for(base, i, view[0], ext)
                 for i, view in enumerate(VIEW_DEFS, 1)]
    out_dir = select_run_folder(out_dir, filenames)
    rendered = []
    old_camera = lux.getCamera()
    try:
        log("KeyShot 版本：{0}".format(lux.getKeyShotVersion()))
        log("场景信息：{0!r}".format(info))
        log("输出目录：{0}".format(out_dir))
        log("尺寸：{0} x {1}；可见零件：{2}".format(width, height, len(bounds)))
        log("渲染方式：本地逐张完成，保留当前渲染质量设置。")
        opts = get_render_options()
        try:
            make_work_camera()
            for index, (label, azimuth, inclination) in enumerate(VIEW_DEFS, 1):
                log("渲染 {0}/8：{1}".format(index, label))
                apply_view(label, azimuth, inclination, bounds, width, height)
                path = os.path.join(out_dir, filenames[index - 1])
                result = lux.renderImage(
                    path=path, width=width, height=height, opts=opts,
                    format=getattr(lux, EXT_TO_FORMAT_CONST[ext]))
                if result is False or not os.path.isfile(path) or os.path.getsize(path) == 0:
                    raise RuntimeError("渲染被取消或未生成图片：{0}".format(path))
                rendered.append(path)
                log("已生成：{0}".format(path))
        finally:
            if old_camera:
                lux.setCamera(old_camera)
            lux.sync()
        log("完成，共生成 {0} 张图片。".format(len(rendered)))
    except BaseException:
        log("未完成。已生成 {0} 张。输出目录：{1}".format(len(rendered), out_dir))
        log(traceback.format_exc())
        raise
    if OPEN_OUTPUT_FOLDER_WHEN_DONE and hasattr(os, "startfile"):
        try:
            os.startfile(out_dir)
        except Exception:
            pass
    message_box("八视图渲染完成，共 {0} 张。\n\n保存位置：\n{1}".format(len(rendered), out_dir))
    return rendered


if __name__ == "__main__":
    try:
        main()
    except Cancelled as exc:
        log(str(exc))
    except Exception as exc:
        log("失败：{0}".format(exc))
        traceback.print_exc()
        message_box("八视图渲染失败：\n\n{0}\n\n"
                    "请查看脚本控制台了解详情。".format(exc),
                    error=True)
        raise
