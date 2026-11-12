import sys, traceback
sys.path.insert(0, r"C:\Users\lixiang\Desktop\SlideForge\analysis")
try:
    import _render_pilot
except Exception as e:
    with open(r"C:\Users\lixiang\Desktop\SlideForge\analysis\_render_err.txt", "w", encoding="utf-8") as f:
        f.write("IMPORT_ERROR\n")
        f.write(traceback.format_exc())
        f.write("\nSTDOUT captured? none\n")
    raise
