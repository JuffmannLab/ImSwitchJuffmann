import threading
import numpy as np
import PySpin
import atexit

from imswitch.imcommon.model import initLogger
from .DetectorManager import (
    DetectorManager, DetectorNumberParameter, DetectorListParameter
)


class FLIRManager(DetectorManager):
    """
    DetectorManager for a FLIR camera using PySpin.
    Mirrors the HamamatsuManager interface so it integrates with DetectorsManager.
    """

    def __init__(self, detectorInfo, name, **_lowLevelManagers):
        self.__logger = initLogger(self, instanceName=name)
        self._lock = threading.RLock()
        self._acquiring = False
        self._last_frame = None
        self._system = None
        self._cam_list = None
        self._cam = None

        # 1) Open camera (no calls into DetectorManager here)
        cam_id = detectorInfo.managerProperties.get('cameraListIndex', 0)
        self._open_camera(cam_id)

        # 2) Read current size/model for constructing the base class
        fullShape = self._get_image_size()
        model = self._get_model()

        # Parameters exposed (mirrors HamamatsuManager)
        parameters = {
            'Set exposure time': DetectorNumberParameter(group='Timings', value=0,
                                                         valueUnits='s', editable=True),
            'Real exposure time': DetectorNumberParameter(group='Timings', value=0,
                                                          valueUnits='s', editable=False),
            'Internal frame interval': DetectorNumberParameter(group='Timings', value=0,
                                                               valueUnits='s', editable=False),
            'Readout time': DetectorNumberParameter(group='Timings', value=0,
                                                    valueUnits='s', editable=False),
            'Internal frame rate': DetectorNumberParameter(group='Timings', value=0,
                                                           valueUnits='fps', editable=False),
            'Trigger source': DetectorListParameter(group='Acquisition mode',
                                                    value='Internal trigger',
                                                    options=['Internal trigger',
                                                             'External "start-trigger"',
                                                             'External "frame-trigger"'],
                                                    editable=True),
            'Gain': DetectorNumberParameter(group='Analog', value=0.0, valueUnits='dB', editable=True),
            'Camera pixel size': DetectorNumberParameter(group='Miscellaneous', value=0.1,
                                                         valueUnits='µm', editable=True)
        }

        super().__init__(detectorInfo, name, fullShape=fullShape, supportedBinnings=[1, 2, 4],
                         model=model, parameters=parameters, croppable=True)

        # Apply initial properties in a safe order
        cfg = dict(detectorInfo.managerProperties.get('flir', {}))

        # Binning first (parsing "2x2" or 2)
        if 'binning' in cfg:
            b = cfg.pop('binning')
            if isinstance(b, str) and 'x' in b:
                b = int(b.lower().split('x')[0])
            else:
                b = int(b)
            self.setBinning(b)

        # ROI (crop): use keys subarray_hpos/vpos/hsize/vsize if provided
        have_roi = all(k in cfg for k in ('subarray_hpos', 'subarray_vpos', 'subarray_hsize', 'subarray_vsize'))
        if have_roi:
            hpos = int(cfg.pop('subarray_hpos'))
            vpos = int(cfg.pop('subarray_vpos'))
            hsize = int(cfg.pop('subarray_hsize'))
            vsize = int(cfg.pop('subarray_vsize'))
            self.crop(hpos, vpos, hsize, vsize)

        # Pixel format / color mode from JSON (not user-editable)
        self._pixel_format_name = 'Mono8'  # default

        pf = None
        if 'pixel_format' in cfg:
            pf = str(cfg.pop('pixel_format'))
        if pf:
            self._set_pixel_format(pf)

        # Exposure
        if 'exposure_time' in cfg:
            exp_s = float(cfg.pop('exposure_time'))
            self._setExposure(exp_s)

        # Gain
        if 'gain' in cfg:
            gain_val = float(cfg.pop('gain'))
            self._setGain(gain_val)

        # Trigger (optional): trigger_source (1 internal, 2 external), trigger_mode (6 AcquisitionStart, 1 FrameStart)
        if 'trigger_source' in cfg or 'trigger_mode' in cfg:
            src = int(cfg.pop('trigger_source', 1))
            mode = int(cfg.pop('trigger_mode', 1))
            if src == 1:
                trig_text = 'Internal trigger'
            else:
                trig_text = 'External "start-trigger"' if mode == 6 else 'External "frame-trigger"'
            self._setTriggerSource(trig_text)

        # Sync UI parameters with camera and initialize "Set exposure time"
        self._updatePropertiesFromCamera()
        super().setParameter('Set exposure time', self.parameters['Real exposure time'].value)

        atexit.register(self.cleanupfunction)

    def __del__(self):
        # Best-effort cleanup; ignore exceptions on interpreter shutdown
        try:
            self.stopAcquisition()
        except Exception:
            pass
        try:
            if self._cam is not None:
                self._cam.DeInit()
        except Exception:
            pass
        try:
            if self._cam_list is not None:
                self._cam_list.Clear()
        except Exception:
            pass
        try:
            if self._system is not None:
                self._system.ReleaseInstance()
        except Exception:
            pass

    @property
    def pixelSizeUm(self):
        umxpx = self.parameters['Camera pixel size'].value
        return [1, umxpx, umxpx]

    # ---------------------------
    # Live acquisition and frames
    # ---------------------------
    def startAcquisition(self):
        with self._lock:
            if self._acquiring:
                return
            self._ensure_continuous_mode()
            self._set_stream_handling()
            self._cam.BeginAcquisition()
            self._acquiring = True

    def stopAcquisition(self):
        with self._lock:
            if not self._acquiring:
                return
            try:
                self._cam.EndAcquisition()
            finally:
                self._acquiring = False

    def getLatestFrame(self, is_save=True):
        with self._lock:
            if not self._acquiring:
                return self._ensure_last_frame()

            last = None
            # Drain any queued frames and keep the most recent
            for _ in range(32):
                try:
                    img = self._cam.GetNextImage(0)  # non-blocking
                except Exception:
                    break
                if not img.IsIncomplete():
                    try:
                        arr = self._image_to_numpy(img)
                        last = arr
                    except Exception:
                        pass
                try:
                    img.Release()
                except Exception:
                    pass

            if last is not None:
                self._last_frame = last
                return last
            return self._ensure_last_frame()

    def getChunk(self):
        # Grab up to a few frames non-blocking
        frames = []
        with self._lock:
            if not self._acquiring:
                return frames
            for _ in range(4):
                try:
                    img = self._cam.GetNextImage(0)
                except Exception:
                    break
                if img.IsIncomplete():
                    img.Release()
                    break
                arr = self._image_to_numpy(img)
                img.Release()
                frames.append(arr)
            return frames

    def flushBuffers(self):
        # No camera-side flush here; just drop our last frame
        self._last_frame = None

    # ---------------------------
    # ROI, binning, parameters
    # ---------------------------
    def crop(self, hpos, vpos, hsize, vsize):
        def cropAction():
            nm = self._cam.GetNodeMap()

            # Reset to offsets 0 first
            self._set_node_int_aligned(nm, 'OffsetX', 0)
            self._set_node_int_aligned(nm, 'OffsetY', 0)

            # Set size then offsets; align to increments
            self._set_node_int_aligned(nm, 'Width', hsize)
            self._set_node_int_aligned(nm, 'Height', vsize)
            self._set_node_int_aligned(nm, 'OffsetX', hpos)
            self._set_node_int_aligned(nm, 'OffsetY', vpos)

        self._performSafeCameraAction(cropAction)

        # Bookkeeping
        self._frameStart = (hpos, vpos)
        self._shape = (hsize, vsize)

    def setBinning(self, binning):
        super().setBinning(binning)

        def setBin():
            nm = self._cam.GetNodeMap()
            self._set_node_int_aligned(nm, 'BinningHorizontal', int(binning))
            self._set_node_int_aligned(nm, 'BinningVertical', int(binning))

        self._performSafeCameraAction(setBin)

    def setParameter(self, name, value):
        super().setParameter(name, value)

        if name == 'Set exposure time':
            self._setExposure(value)
            self._updatePropertiesFromCamera()
        elif name == 'Trigger source':
            self._setTriggerSource(value)
        elif name == 'Gain':
            self._setGain(float(value))
            # Reflect the actual value after clamping
            super().setParameter('Gain', self._get_gain() or 0.0)

        return self.parameters

    # ---------------------------
    # Internals: parameters -> nodes
    # ---------------------------
    def _setExposure(self, time_s):
        nm = self._cam.GetNodeMap()
        # Turn off auto exposure when explicitly setting
        self._set_enum_if_available(nm, 'ExposureAuto', 'Off')
        # ExposureTime in microseconds
        us = max(0.0, float(time_s) * 1e6)
        self._set_node_float_clamped(nm, 'ExposureTime', us)

    def _setGain(self, gain_value):
        nm = self._cam.GetNodeMap()
        # Turn off auto gain when explicitly setting
        self._set_enum_if_available(nm, 'GainAuto', 'Off')
        # Gain is usually in dB on FLIR cameras
        self._set_node_float_clamped(nm, 'Gain', float(gain_value))

    def _setTriggerSource(self, source):
        nm = self._cam.GetNodeMap()
        # Internal trigger = free run
        if source == 'Internal trigger':
            self._set_enum_if_available(nm, 'TriggerMode', 'Off')

        elif source == 'External "start-trigger"':
            self._set_enum_if_available(nm, 'TriggerSelector', 'AcquisitionStart')
            self._set_enum_if_available(nm, 'TriggerSource', 'Line0')
            self._set_enum_if_available(nm, 'TriggerActivation', 'RisingEdge')
            self._set_enum_if_available(nm, 'TriggerMode', 'On')

        elif source == 'External "frame-trigger"':
            self._set_enum_if_available(nm, 'TriggerSelector', 'FrameStart')
            self._set_enum_if_available(nm, 'TriggerSource', 'Line0')
            self._set_enum_if_available(nm, 'TriggerActivation', 'RisingEdge')
            self._set_enum_if_available(nm, 'TriggerMode', 'On')
        else:
            raise ValueError(f'Invalid trigger source "{source}"')

    def _performSafeCameraAction(self, function):
        try:
            with self._lock:
                function()
        except Exception:
            self.stopAcquisition()
            with self._lock:
                function()
            self.startAcquisition()

    def _updatePropertiesFromCamera(self):
        # Exposure time (s)
        super().setParameter('Real exposure time', self._get_exposure_time_s())

        # Frame rate and interval
        fps = self._get_frame_rate()
        super().setParameter('Internal frame rate', fps if fps is not None else 0.0)
        if fps and fps > 0:
            super().setParameter('Internal frame interval', 1.0 / fps)
        else:
            super().setParameter('Internal frame interval',
                                 self.parameters['Real exposure time'].value)

        # Readout time (not provided by camera → 0.0 or your estimate)
        super().setParameter('Readout time', 0.0)

        # Gain
        g = self._get_gain()
        if g is not None:
            super().setParameter('Gain', g)

        # Trigger source text: only push to UI during initial sync (see next step)
        trig_src_text = self._get_trigger_source_text()
        if trig_src_text and getattr(self, '_initializing', False):
            super().setParameter('Trigger source', trig_src_text)

    # ---------------------------
    # Camera open/config helpers
    # ---------------------------
    def _open_camera(self, cam_id):
        if PySpin is None:
            raise RuntimeError('PySpin is not available; install FLIR Spinnaker SDK and PySpin')

        try:
            self._system = PySpin.System.GetInstance()
            self._cam_list = self._system.GetCameras()
            if self._cam_list.GetSize() <= int(cam_id):
                raise RuntimeError(f'No FLIR camera at index {cam_id}')

            self.__logger.debug(f'Trying to initialize FLIR camera {cam_id}')
            self._cam = self._cam_list.GetByIndex(int(cam_id))
            self._cam.Init()

            # Basic defaults
            self._ensure_continuous_mode()
            self._set_stream_handling()
            self._set_pixel_format('Mono8')

            self.__logger.info(f'Initialized camera, model: {self._get_model()}')

        except Exception as e:
            # Make sure to release resources if init failed midway
            try:
                if self._cam is not None:
                    self._cam.DeInit()
            except Exception:
                pass
            try:
                if self._cam_list is not None:
                    self._cam_list.Clear()
            except Exception:
                pass
            try:
                if self._system is not None:
                    self._system.ReleaseInstance()
            except Exception:
                pass
            raise RuntimeError(f'Failed to initialize FLIR camera {cam_id}: {e}') from e

    def _ensure_continuous_mode(self):
        nm = self._cam.GetNodeMap()
        self._set_enum_if_available(nm, 'AcquisitionMode', 'Continuous')

    def _set_stream_handling(self):
        try:
            s_map = self._cam.GetTLStreamNodeMap()

            # Prefer explicit manual buffer count if supported
            mode = PySpin.CEnumerationPtr(s_map.GetNode('StreamBufferCountMode'))
            if PySpin.IsAvailable(mode) and PySpin.IsWritable(mode):
                manual = mode.GetEntryByName('Manual')
                if PySpin.IsAvailable(manual) and PySpin.IsReadable(manual):
                    mode.SetIntValue(manual.GetValue())
                    cnt = PySpin.CIntegerPtr(s_map.GetNode('StreamBufferCount'))
                    if PySpin.IsAvailable(cnt) and PySpin.IsWritable(cnt):
                        cnt.SetValue(4)  # small ring for live view

            # Fallback if only the default-count node is exposed
            cnt_def = PySpin.CIntegerPtr(s_map.GetNode('StreamDefaultBufferCount'))
            if PySpin.IsAvailable(cnt_def) and PySpin.IsWritable(cnt_def):
                cnt_def.SetValue(4)

            # Deliver the newest frame for LV (drop older ones)
            handling = PySpin.CEnumerationPtr(s_map.GetNode('StreamBufferHandlingMode'))
            if PySpin.IsAvailable(handling) and PySpin.IsWritable(handling):
                newest_only = handling.GetEntryByName('NewestOnly')
                if PySpin.IsAvailable(newest_only) and PySpin.IsReadable(newest_only):
                    handling.SetIntValue(newest_only.GetValue())
        except Exception:
            pass

    def _set_pixel_format(self, fmt_name):
        nm = self._cam.GetNodeMap()
        try:
            pix = PySpin.CEnumerationPtr(nm.GetNode('PixelFormat'))
            if not (PySpin.IsAvailable(pix) and PySpin.IsWritable(pix)):
                raise RuntimeError('PixelFormat node not available/writable')
            entry = pix.GetEntryByName(fmt_name)
            if not (PySpin.IsAvailable(entry) and PySpin.IsReadable(entry)):
                raise RuntimeError(f'PixelFormat "{fmt_name}" not available on this camera')
            pix.SetIntValue(entry.GetValue())
            self._pixel_format_name = fmt_name
            self.__logger.info(f'Set PixelFormat to {fmt_name}')
        except Exception as e:
            # Fallback to Mono8
            self.__logger.warning(f'Failed to set PixelFormat "{fmt_name}" ({e}); falling back to Mono8')
            try:
                mono8_entry = PySpin.CEnumerationPtr(nm.GetNode('PixelFormat')).GetEntryByName('Mono8')
                PySpin.CEnumerationPtr(nm.GetNode('PixelFormat')).SetIntValue(mono8_entry.GetValue())
                self._pixel_format_name = 'Mono8'
            except Exception:
                pass

    def _get_image_size(self):
        nm = self._cam.GetNodeMap()
        w = self._get_node_int(nm, 'Width') or 640
        h = self._get_node_int(nm, 'Height') or 480
        return (int(w), int(h))

    def _get_model(self):
        try:
            return self._cam.DeviceModelName.GetValue()
        except Exception:
            return 'FLIR'

    # ---------------------------
    # Node helpers
    # ---------------------------
    def _set_node_float_clamped(self, nm, node_name, value):
        n = PySpin.CFloatPtr(nm.GetNode(node_name))
        if not (PySpin.IsAvailable(n) and PySpin.IsWritable(n)):
            raise RuntimeError(f'Node {node_name} not available/writable')
        v = float(value)
        v = max(n.GetMin(), min(n.GetMax(), v))
        n.SetValue(v)

    def _get_node_float(self, nm, node_name):
        n = PySpin.CFloatPtr(nm.GetNode(node_name))
        if not (PySpin.IsAvailable(n) and PySpin.IsReadable(n)):
            return None
        return n.GetValue()

    def _set_node_int_aligned(self, nm, node_name, value):
        n = PySpin.CIntegerPtr(nm.GetNode(node_name))
        if not (PySpin.IsAvailable(n) and PySpin.IsWritable(n)):
            raise RuntimeError(f'Node {node_name} not available/writable')
        inc = n.GetInc() if hasattr(n, 'GetInc') else 1
        v = int(value)
        if inc and inc > 1:
            v = (v // inc) * inc
        v = max(n.GetMin(), min(n.GetMax(), v))
        n.SetValue(v)

    def _get_node_int(self, nm, node_name):
        n = PySpin.CIntegerPtr(nm.GetNode(node_name))
        if not (PySpin.IsAvailable(n) and PySpin.IsReadable(n)):
            return None
        return n.GetValue()

    def _set_enum_if_available(self, nm, node_name, entry_name):
        try:
            e = PySpin.CEnumerationPtr(nm.GetNode(node_name))
            if not (PySpin.IsAvailable(e) and PySpin.IsWritable(e)):
                return False
            en = e.GetEntryByName(entry_name)
            if not (PySpin.IsAvailable(en) and PySpin.IsReadable(en)):
                return False
            e.SetIntValue(en.GetValue())
            return True
        except Exception:
            return False

    def _get_enum_name(self, nm, node_name):
        try:
            e = PySpin.CEnumerationPtr(nm.GetNode(node_name))
            if not (PySpin.IsAvailable(e) and PySpin.IsReadable(e)):
                return None
            val = e.GetIntValue()
            en = e.GetEntry(val)
            if PySpin.IsAvailable(en) and PySpin.IsReadable(en):
                return en.GetName()
            return None
        except Exception:
            return None

    # ---------------------------
    # Property helpers used by _updatePropertiesFromCamera
    # ---------------------------
    def _get_exposure_time_s(self):
        nm = self._cam.GetNodeMap()
        us = self._get_node_float(nm, 'ExposureTime')
        return float(us) / 1e6 if us is not None else 0.0

    def _get_frame_rate(self):
        nm = self._cam.GetNodeMap()
        afr = self._get_node_float(nm, 'AcquisitionFrameRate')
        return float(afr) if afr is not None else None

    def _get_gain(self):
        nm = self._cam.GetNodeMap()
        g = self._get_node_float(nm, 'Gain')
        return float(g) if g is not None else None

    def _get_trigger_source_text(self):
        nm = self._cam.GetNodeMap()
        mode = self._get_enum_name(nm, 'TriggerMode')  # On/Off
        if mode == 'Off':
            return 'Internal trigger'
        sel = self._get_enum_name(nm, 'TriggerSelector')  # FrameStart/AcquisitionStart
        if sel == 'AcquisitionStart':
            return 'External "start-trigger"'
        return 'External "frame-trigger"'

    # ---------------------------
    # Image conversion
    # ---------------------------
    def _image_to_numpy(self, img):
        try:
            target_pf = (self._pixel_format_name or 'Mono8').upper()

            # Mono8 output
            if target_pf == 'MONO8':
                if img.GetPixelFormat() != PySpin.PixelFormat_Mono8:
                    conv = img.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
                else:
                    conv = img
                arr = conv.GetNDArray()
                if arr is None:
                    h, w = conv.GetHeight(), conv.GetWidth()
                    arr = np.frombuffer(conv.GetData(), dtype=np.uint8).reshape((h, w))
                return arr

            # BGR8 output
            if target_pf == 'BGR8':
                if img.GetPixelFormat() != PySpin.PixelFormat_RGB8:
                    conv = img.Convert(PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)
                else:
                    conv = img
                arr = conv.GetNDArray()  # shape (H, W, 3)
                if arr is None:
                    h, w = conv.GetHeight(), conv.GetWidth()
                    arr = np.frombuffer(conv.GetData(), dtype=np.uint8).reshape((h, w, 3))
                return arr

            # If user selected a Bayer format, convert to RGB8 for display
            if target_pf.startswith('BAYER'):
                conv = img.Convert(PySpin.PixelFormat_RGB8, PySpin.HQ_LINEAR)
                arr = conv.GetNDArray()
                if arr is None:
                    h, w = conv.GetHeight(), conv.GetWidth()
                    arr = np.frombuffer(conv.GetData(), dtype=np.uint8).reshape((h, w, 3))
                return arr

            # Default fallback: try Mono8
            conv = img.Convert(PySpin.PixelFormat_Mono8, PySpin.HQ_LINEAR)
            arr = conv.GetNDArray()
            if arr is None:
                h, w = conv.GetHeight(), conv.GetWidth()
                arr = np.frombuffer(conv.GetData(), dtype=np.uint8).reshape((h, w))
            return arr

        except Exception:
            # Conservative fallback
            h, w = img.GetHeight(), img.GetWidth()
            try:
                raw = np.frombuffer(img.GetData(), dtype=np.uint8)
                if raw.size == h * w * 3:
                    return raw.reshape((h, w, 3))
                return raw.reshape((h, w))
            except Exception:
                return np.zeros((h, w), dtype=np.uint8)

    def _ensure_last_frame(self):
        if self._last_frame is not None:
            return self._last_frame
        w, h = self.fullShape[0], self.fullShape[1]
        self._last_frame = np.zeros((h, w), dtype=np.uint8)
        return self._last_frame

    # ---------------------------
    # Property application facade (for potential future use)
    # ---------------------------
    def _set_property(self, name, value):
        if name == 'exposure_time':
            self._setExposure(float(value))
        elif name == 'binning':
            b = value
            if isinstance(b, (bytes, bytearray)):
                b = b.decode('ascii').lower().strip()
            if isinstance(b, str) and 'x' in b:
                b = int(b.split('x')[0])
            self.setBinning(int(b))
        elif name in ('subarray_hpos', 'subarray_vpos', 'subarray_hsize', 'subarray_vsize'):
            # Prefer calling crop() once with all ROI params
            pass
        elif name == 'trigger_source':
            src_text = 'Internal trigger' if int(value) == 1 else 'External "frame-trigger"'
            self._setTriggerSource(src_text)
        elif name == 'trigger_mode':
            mode = int(value)
            if mode == 6:
                self._setTriggerSource('External "start-trigger"')
            elif mode == 1:
                self._setTriggerSource('External "frame-trigger"')
        # Extend as needed


    def cleanupfunction(self):
        try:
            self.stopAcquisition()
        except Exception:
            pass
        try:
            if self._cam is not None:
                self._cam.DeInit()
        except Exception:
            pass
        try:
            if self._cam_list is not None:
                self._cam_list.Clear()
        except Exception:
            pass
        try:
            if self._system is not None:
                self._system.ReleaseInstance()
        except Exception:
            pass