import os
os.environ['MPLBACKEND'] = 'Agg'  # 强制使用 Agg 后端，避免 InterAgg 报错

# 依赖：Pillow, numpy, matplotlib, scikit-image, shapely, scipy
from PIL import Image
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 双保险
import matplotlib.pyplot as plt
from matplotlib.colors import rgb_to_hsv
from skimage.morphology import skeletonize
from shapely.geometry import LineString
from shapely.ops import linemerge
from scipy.signal import savgol_filter
from scipy.spatial import cKDTree

# 路径参数
IMG_PATH = 'Curve.png'              # 你的曲线图片
OUT_PATH = 'Curve_with_offsets.png' # 输出

# 偏移设置（像素）
d = 15
counts = [1, 2, 3]
side = 'left'  # 'left' 或 'right'

# 读取图片
img = Image.open(IMG_PATH).convert('RGB')
rgb = np.asarray(img).astype(np.float32) / 255.0

# HSV 阈值提取黄色（按需微调）
hsv = rgb_to_hsv(rgb)
H, S, V = hsv[...,0], hsv[...,1], hsv[...,2]
mask = (H >= 0.12) & (H <= 0.18) & (S >= 0.2) & (V >= 0.6)
mask = mask.astype(np.uint8)

# 骨架化
skel = skeletonize(mask).astype(np.uint8)

# 提取骨架点并近邻追踪
pts = np.column_stack(np.where(skel > 0))[:, ::-1]  # (x,y)
if len(pts) < 2:
    raise RuntimeError("未检测到曲线骨架，请调整 HSV 阈值或检查图片颜色。")

tree = cKDTree(pts)
used = np.zeros(len(pts), dtype=bool)
path = []
i = np.argmax(pts[:,0])  # 从最右端点开始
while True:
    path.append(pts[i])
    used[i] = True
    dists, idxs = tree.query(pts[i], k=10, distance_upper_bound=2.0)
    candidates = [idx for idx in np.atleast_1d(idxs)
                  if idx < len(pts) and not used[idx] and idx != i]
    if not candidates:
        break
    i = candidates[0]
path = np.array(path)

# 平滑
n = len(path)
win = min(21, n if n % 2 == 1 else n - 1)
win = max(win, 7)  # 确保奇数且不小于 7
xs = savgol_filter(path[:,0], win, 3, mode='interp')
ys = savgol_filter(path[:,1], win, 3, mode='interp')
line = LineString(np.column_stack([xs, ys]))

# 生成三条法线等距偏移
offs = [line.parallel_offset(d*k, side=side, join_style=1) for k in counts]

# 绘制并保存
plt.figure(figsize=(10,3))
plt.imshow(rgb)
plt.plot(xs, ys, color='orange', linewidth=1.8, label='Base')
colors = ['#ff4d4f','#52c41a','#1677ff']
for k, o in enumerate(offs):
    if o.is_empty:
        continue
    if o.geom_type == 'MultiLineString':
        o = linemerge(o)
    ox, oy = o.xy
    plt.plot(ox, oy, color=colors[k], linewidth=1.5, label=f'Offset {(k+1)*d}px {side}')
plt.axis('off'); plt.legend(); plt.tight_layout()
plt.savefig(OUT_PATH, dpi=200, bbox_inches='tight')
print(f"已保存：{OUT_PATH}")
