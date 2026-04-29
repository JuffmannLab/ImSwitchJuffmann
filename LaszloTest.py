from pyKDC101 import KDC

kdc = KDC()
kdc.Open()
print(kdc.GetPos())
kdc.Close()