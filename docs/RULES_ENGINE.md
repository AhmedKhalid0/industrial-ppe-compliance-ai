# Industrial PPE Compliance: Rules Engine & Spatial Reasoning

Author: Ahmed Khaled (Ahmed Algendy)  
Email: contact@ahmedalgendy.com  
GitHub: [https://github.com/AhmedKhalid0](https://github.com/AhmedKhalid0)  
Website: [https://ahmedalgendy.com](https://ahmedalgendy.com)  

---

## 1. Spatial Containment & Zone Logic

The compliance engine evaluates spatial intersections between worker bounding boxes $B_{\text{worker}}$ and individual PPE detections $B_{\text{ppe}}$:

1. **Headgear Containment ($B_{\text{helmet}} \subset B_{\text{worker}}$)**:
   * Vertical upper quantile check: $y_{\text{center}}(\text{helmet}) \le y_{\text{min}}(\text{worker}) + 0.35 \times h_{\text{worker}}$.
   * Horizontal alignment: $|x_{\text{center}}(\text{helmet}) - x_{\text{center}}(\text{worker})| \le 0.25 \times w_{\text{worker}}$.
2. **High-Visibility Vest ($B_{\text{vest}} \subset B_{\text{worker}}$)**:
   * Mid-torso intersection ratio: $\text{IoU}(B_{\text{vest}}, B_{\text{torso}}) \ge 0.40$.

---

## 2. Temporal Debounce & False Positive Filtering

To prevent single-frame occlusion spikes from triggering false alarms, violations must persist across $N=4$ consecutive video frames before an incident record and snapshot are committed to the database.
