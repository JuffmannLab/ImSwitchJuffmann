import PySpin
import sys

def get_node_str(nodemap, name, default=""):
    try:
        node = PySpin.CStringPtr(nodemap.GetNode(name))
        if PySpin.IsReadable(node):
            return node.GetValue()
    except Exception:
        pass
    return default

def get_node_int(nodemap, name, default=None):
    try:
        node = PySpin.CIntegerPtr(nodemap.GetNode(name))
        if PySpin.IsReadable(node):
            return int(node.GetValue())
    except Exception:
        pass
    return default

def format_ip_from_int(val):
    if val is None:
        return ""
    # GenICam stores IP in a 32-bit integer (often little-endian)
    octets = [(val >> (8 * i)) & 0xFF for i in range(4)]
    return ".".join(str(o) for o in octets[::-1])

def format_mac_from_int(val):
    if val is None:
        return ""
    return ":".join(f"{(val >> (8 * i)) & 0xFF:02X}" for i in range(5, -1, -1))

def main():
    system = PySpin.System.GetInstance()

    try:
        # Enumerate interfaces (NICs, USB controllers)
        iface_list = system.GetInterfaces()
        num_ifaces = iface_list.GetSize()
        print(f"Found {num_ifaces} interface(s).")
        print("=" * 70)

        total_cams = 0

        for i in range(num_ifaces):
            iface = iface_list.GetByIndex(i)
            try:
                tl_iface = iface.GetTLNodeMap()
                iface_name = get_node_str(tl_iface, "InterfaceDisplayName", "<n/a>")
                iface_id = get_node_str(tl_iface, "InterfaceID", "<n/a>")
                iface_type = get_node_str(tl_iface, "InterfaceType", "")  # often "GEV" or "U3V"

                # Optional: NIC details for GigE interfaces
                gev_iface_ip = format_ip_from_int(get_node_int(tl_iface, "GevInterfaceSubnetIPAddress"))
                gev_iface_mac = format_mac_from_int(get_node_int(tl_iface, "GevInterfaceMACAddress"))

                print(f"[IF {i}] {iface_name} (ID: {iface_id})  Type: {iface_type or '<unknown>'}")
                if gev_iface_ip or gev_iface_mac:
                    print(f"       NIC IP={gev_iface_ip or '<n/a>'}  MAC={gev_iface_mac or '<n/a>'}")

                # Cameras visible on this interface
                cam_list = iface.GetCameras()
                num_cams = cam_list.GetSize()
                total_cams += num_cams
                print(f"       Cameras on this interface: {num_cams}")

                for j in range(num_cams):
                    cam = cam_list.GetByIndex(j)
                    try:
                        tl_dev = cam.GetTLDeviceNodeMap()

                        vendor = get_node_str(tl_dev, "DeviceVendorName", "")
                        model = get_node_str(tl_dev, "DeviceModelName", "<unknown>")
                        serial = get_node_str(tl_dev, "DeviceSerialNumber", "")
                        dev_type = get_node_str(tl_dev, "DeviceType", "")  # e.g., "GigEVision" or "USB3Vision"

                        # Connection details
                        conn_lines = []
                        if "GigE" in dev_type or "GEV" in dev_type or dev_type == "GigEVision":
                            ip = format_ip_from_int(get_node_int(tl_dev, "GevDeviceIPAddress"))
                            mac = format_mac_from_int(get_node_int(tl_dev, "GevDeviceMACAddress"))
                            subnet = format_ip_from_int(get_node_int(tl_dev, "GevDeviceSubnetMask"))
                            conn_lines.append(f"GigE IP={ip or '<n/a>'}  MAC={mac or '<n/a>'}  Subnet={subnet or '<n/a>'}")
                        elif "USB" in dev_type or "U3V" in dev_type or dev_type == "USB3Vision":
                            guid = get_node_str(tl_dev, "DeviceGUID", "")
                            addr = get_node_int(tl_dev, "DeviceAddress")
                            speed = get_node_str(tl_dev, "DeviceCurrentSpeed", "")
                            port_path = get_node_str(tl_dev, "DevicePortPath", "")  # may not exist on all systems
                            parts = []
                            if guid: parts.append(f"GUID={guid}")
                            if addr is not None: parts.append(f"Address={addr}")
                            if speed: parts.append(f"Speed={speed}")
                            if port_path: parts.append(f"PortPath={port_path}")
                            conn_lines.append("USB " + "  ".join(parts) if parts else "USB <no details>")
                        else:
                            # Fallback: try both
                            ip = format_ip_from_int(get_node_int(tl_dev, "GevDeviceIPAddress"))
                            guid = get_node_str(tl_dev, "DeviceGUID", "")
                            if ip:
                                conn_lines.append(f"GigE IP={ip}")
                            if guid:
                                conn_lines.append(f"USB GUID={guid}")

                        # Interface info sometimes mirrored at device level
                        iface_name_dev = get_node_str(tl_dev, "InterfaceDisplayName", "")
                        iface_id_dev = get_node_str(tl_dev, "InterfaceID", "")

                        print(f"   - [{j}] {vendor} {model} (S/N: {serial})")
                        print(f"        Type: {dev_type or '<unknown>'}")
                        if iface_name_dev or iface_id_dev:
                            print(f"        Interface: {iface_name_dev or '<n/a>'} (ID: {iface_id_dev or '<n/a>'})")
                        # Connection summary
                        if conn_lines:
                            for line in conn_lines:
                                print(f"        Connection: {line}")
                        else:
                            print("        Connection: <n/a>")

                    except Exception as e:
                        print(f"   - [{j}] Error reading camera info: {e}", file=sys.stderr)
                    finally:
                        # Release cam object reference
                        del cam

                # Clear and delete camera list for this interface
                cam_list.Clear()
                del cam_list
                print("-" * 70)

            except Exception as e:
                print(f"[IF {i}] Error: {e}", file=sys.stderr)
            finally:
                del iface

        # Clear and delete interface list before releasing the system
        iface_list.Clear()
        del iface_list

        ver = system.GetLibraryVersion()
        print(f"Total cameras: {total_cams}")
        print(f"Spinnaker SDK library: {ver.major}.{ver.minor}.{ver.type}.{ver.build}")

    finally:
        # At this point no cam/iface references remain
        system.ReleaseInstance()

if __name__ == "__main__":
    main()