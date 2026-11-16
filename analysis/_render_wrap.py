import os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import _render_pilot
except Exception as e:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_render_err.txt"), "w", encoding="utf-8") as f:
        f.write("IMPORT_ERROR\n")
        f.write(traceback.format_exc())
        f.write("\nSTDOUT captured? none\n")
    raise
