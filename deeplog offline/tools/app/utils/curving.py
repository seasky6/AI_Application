import cv2, numpy as np, matplotlib.pyplot as plt
from skimage.morphology import skeletonize
from shapely.geometry import LineString
from shapely.ops import linemerge
from scipy.spatial import cKDTree

img = cv2.imread('Curve.png')
hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
# 以黄色为例的阈值（按需微调）
lower = np.array([15, 50, 150]); upper = np.array([40, 255, 255])
mask = cv2.inRange(hsv, lower, upper)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
skel = skeletonize((mask>0).astype(np.uint8)).astype(np.uint8)

# 提取骨架坐标并按路径顺序排序（简化版）
pts = np.column_stack(np.where(skel>0))[:, ::-1]  # (x,y)
tree = cKDTree(pts); used = np.zeros(len(pts), bool)
path = []
i = np.argmax(pts[:,0])  # 从最右端点开始，作为简化
while True:
    path.append(pts[i])
    used[i] = True
    d, j = tree.query(pts[i], k=10, distance_upper_bound=2.0)
    candidates = [idx for idx in np.atleast_1d(j) if idx < len(pts) and not used[idx] and idx!=i]
    if not candidates: break
    i = candidates[0]
path = np.array(path)

# 平滑并转为 LineString
from scipy.signal import savgol_filter
xs = savgol_filter(path[:,0], 21, 3, mode='interp')
ys = savgol_filter(path[:,1], 21, 3, mode='interp')
line = LineString(np.column_stack([xs, ys]))

# 生成同侧三条偏移（像素单位）
d = 15  # 修改为你的偏移像素
offs = [line.parallel_offset(d*k, side='left', join_style=1) for k in [1,2,3]]

# 绘制
plt.figure(figsize=(10,3))
plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
plt.plot(xs, ys, color='orange', linewidth=1.5, label='Base')
colors = ['#ff4d4f','#52c41a','#1677ff']
for k, o in enumerate(offs):
    if o.is_empty: continue
    if o.geom_type == 'MultiLineString':
        o = linemerge(o)
    ox, oy = o.xy
    plt.plot(ox, oy, color=colors[k], linewidth=1.2, label=f'Offset { (k+1)*d }px')
plt.axis('off'); plt.legend(); plt.tight_layout(); plt.show()
