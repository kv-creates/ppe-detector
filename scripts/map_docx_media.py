"""Match embedded media to source PNGs by pixel dimensions."""
import struct
import zipfile

FIGS = ["source_breakdown", "class_dist", "bbox_dist", "sample_grid",
        "resolution_hist", "colab_n_results", "colab_s_results",
        "colab_m_results", "colab_m_conf", "colab_s_conf", "colab_m_PR",
        "colab_m_F1", "colab_m_valbatch", "local_grid", "local_table",
        "ui_live", "ui_log", "ui_analytics", "ui_kpi"]


def png_size(path):
    with open(path, "rb") as fh:
        d = fh.read(33)
    w, h = struct.unpack(">II", d[16:24])
    return (w, h)


z = zipfile.ZipFile("reports/final_report.docx")
for i in range(1, 22):
    for ext in ("png", "jpg"):
        n = f"word/media/image{i}.{ext}"
        if n in z.namelist():
            w, h = struct.unpack(">II", z.read(n)[16:24])
            print(f"image{i}.{ext}: {w}x{h}")
            break
