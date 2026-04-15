import libximc.highlevel as ximc
a = ximc.Axis(r"xi-com:\\.\COM3"); a.open_device()
try:
    print(int(a.get_position().CurPosition))
finally:
    a.close_device()