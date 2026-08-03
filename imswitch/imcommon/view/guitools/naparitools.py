from abc import abstractmethod

import napari
import numpy as np
from napari.utils.translations import trans
from qtpy import QtCore, QtGui, QtWidgets
from vispy.color import Color
from vispy.scene.visuals import Compound, Line, Markers
from vispy.visuals.transforms import STTransform

from .imagetools import minmaxLevels


def addNapariGrayclipColormap():
    if hasattr(napari.utils.colormaps.AVAILABLE_COLORMAPS, 'grayclip'):
        return

    grayclip = []
    for i in range(255):
        grayclip.append([i / 255, i / 255, i / 255])
    grayclip.append([1, 0, 0])
    napari.utils.colormaps.AVAILABLE_COLORMAPS['grayclip'] = napari.utils.Colormap(
        name='grayclip', colors=grayclip
    )


class EmbeddedNapari(napari.Viewer):
    """ Napari viewer to be embedded in non-napari windows. Also includes a
    feature to protect certain layers from being removed when added using
    the add_image method. """

    def __init__(self, *args, show=False, **kwargs):
        super().__init__(*args, show=show, **kwargs)

        # Monkeypatch layer removal methods
        oldDelitemIndices = self.layers._delitem_indices

        def newDelitemIndices(key):
            indices = oldDelitemIndices(key)
            for index in indices[:]:
                layer = index[0][index[1]]
                if hasattr(layer, 'protected') and layer.protected:
                    indices.remove(index)
            return indices

        self.layers._delitem_indices = newDelitemIndices

        # Make menu bar not native
        self.window._qt_window.menuBar().setNativeMenuBar(False)

        # Remove unwanted menu bar items
        menuChildren = self.window._qt_window.findChildren(QtWidgets.QAction)
        for menuChild in menuChildren:
            try:
                if menuChild.text() in [trans._('Close Window'), trans._('Exit')]:
                    self.window.file_menu.removeAction(menuChild)
            except Exception:
                pass

    def add_image(self, *args, protected=False, **kwargs):
        result = super().add_image(*args, **kwargs)

        if isinstance(result, list):
            for layer in result:
                layer.protected = protected
        else:
            result.protected = protected

        return result

    def get_widget(self):
        return self.window._qt_window


class NapariBaseWidget(QtWidgets.QWidget):
    """ Base class for Napari widgets. """

    @property
    @abstractmethod
    def name(self):
        pass

    def __init__(self, napariViewer):
        super().__init__()
        self.viewer = napariViewer

    @classmethod
    def addToViewer(cls, napariViewer):
        """ Adds this widget to the specified Napari viewer. """

        # Add dock for this widget
        widget = cls(napariViewer)
        napariViewer.window.add_dock_widget(widget, name=widget.name, area='left')

        # Move layer list to bottom
        napariViewer.window._qt_window.removeDockWidget(
            napariViewer.window.qt_viewer.dockLayerList
        )
        napariViewer.window._qt_window.addDockWidget(
            napariViewer.window.qt_viewer.dockLayerList.qt_area,
            napariViewer.window.qt_viewer.dockLayerList
        )
        napariViewer.window.qt_viewer.dockLayerList.show()
        return widget

    def addItemToViewer(self, item):
        item.attach(self.viewer,
                    canvas=self.viewer.window.qt_viewer.canvas,
                    view=self.viewer.window.qt_viewer.view,
                    parent=self.viewer.window.qt_viewer.view.scene,
                    order=1e6 + 8000)


class NapariUpdateLevelsWidget(NapariBaseWidget):
    """ Napari widget for auto-levelling the currently selected layer with a
    single click. """

    @property
    def name(self):
        return 'update levels widget'

    def __init__(self, napariViewer):
        super().__init__(napariViewer)

        # Update levels button
        self.updateLevelsButton = QtWidgets.QPushButton('Update levels')
        self.updateLevelsButton.clicked.connect(self._on_update_levels)

        # Layout
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().addWidget(self.updateLevelsButton)

        # Make sure widget isn't too big
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Maximum))

    def _on_update_levels(self):
        for layer in self.viewer.layers.selected:
            layer.contrast_limits = minmaxLevels(layer.data)


class NapariShiftWidget(NapariBaseWidget):
    """ Napari widget for shifting the currently selected layer by a
    user-defined number of pixels. """

    @property
    def name(self):
        return 'image shift controls'

    def __init__(self, napariViewer):
        super().__init__(napariViewer)

        # Title label
        self.titleLabel = QtWidgets.QLabel('<h3>Image shift controls</h3>')

        # Shift up button
        self.upButton = QtWidgets.QPushButton()
        self.upButton.setToolTip('Shift selected layer up')
        self.upButton.setIcon(QtGui.QIcon(f':/themes/{self.viewer.theme}/up_arrow.svg'))
        self.upButton.clicked.connect(self._on_up)

        # Shift right button
        self.rightButton = QtWidgets.QPushButton()
        self.rightButton.setToolTip('Shift selected layer right')
        self.rightButton.setIcon(QtGui.QIcon(f':/themes/{self.viewer.theme}/right_arrow.svg'))
        self.rightButton.clicked.connect(self._on_right)

        # Shift down button
        self.downButton = QtWidgets.QPushButton()
        self.downButton.setToolTip('Shift selected layer down')
        self.downButton.setIcon(QtGui.QIcon(f':/themes/{self.viewer.theme}/down_arrow.svg'))
        self.downButton.clicked.connect(self._on_down)

        # Shift left button
        self.leftButton = QtWidgets.QPushButton()
        self.leftButton.setToolTip('Shift selected layer left')
        self.leftButton.setIcon(QtGui.QIcon(f':/themes/{self.viewer.theme}/left_arrow.svg'))
        self.leftButton.clicked.connect(self._on_left)

        # Reset button
        self.resetButton = QtWidgets.QPushButton('Reset')
        self.resetButton.clicked.connect(self._on_reset)

        # Shift distance field
        self.shiftDistanceLabel = QtWidgets.QLabel('Shift distance:')
        self.shiftDistanceInput = QtWidgets.QSpinBox()
        self.shiftDistanceInput.setMinimum(1)
        self.shiftDistanceInput.setMaximum(9999)
        self.shiftDistanceInput.setValue(1)
        self.shiftDistanceInput.setSuffix(' px')

        # Layout
        self.buttonGrid = QtWidgets.QGridLayout()
        self.buttonGrid.setSpacing(6)
        self.buttonGrid.addWidget(self.upButton, 0, 1)
        self.buttonGrid.addWidget(self.rightButton, 1, 2)
        self.buttonGrid.addWidget(self.downButton, 2, 1)
        self.buttonGrid.addWidget(self.leftButton, 1, 0)
        self.buttonGrid.addWidget(self.resetButton, 1, 1)

        self.shiftDistanceLayout = QtWidgets.QHBoxLayout()
        self.shiftDistanceLayout.setSpacing(12)
        self.shiftDistanceLayout.addWidget(self.shiftDistanceLabel)
        self.shiftDistanceLayout.addWidget(self.shiftDistanceInput, 1)

        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(24)
        self.layout().addWidget(self.titleLabel)
        self.layout().addLayout(self.buttonGrid)
        self.layout().addLayout(self.shiftDistanceLayout)

        # Make sure widget isn't too big
        self.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                                 QtWidgets.QSizePolicy.Maximum))

    def _on_up(self):
        self._do_shift(0, -self._get_shift_distance())

    def _on_right(self):
        self._do_shift(self._get_shift_distance(), 0)

    def _on_down(self):
        self._do_shift(0, self._get_shift_distance())

    def _on_left(self):
        self._do_shift(-self._get_shift_distance(), 0)

    def _on_reset(self):
        for layer in self.viewer.layers.selected:
            layer.translate = [0, 0]

    def _do_shift(self, xDist, yDist):
        for layer in self.viewer.layers.selected:
            y, x = layer.translate
            layer.translate = [y + yDist, x + xDist]

    def _get_shift_distance(self):
        return self.shiftDistanceInput.value()


class VispyBaseVisual(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self._viewer = None
        self._view = None
        self._canvas = None
        self._nodes = []
        self._visible = True
        self._attached = False

    def attach(self, viewer, view, canvas, parent=None, order=0):
        self._viewer = viewer
        self._view = view
        self._canvas = canvas
        self._attached = True

    def detach(self):
        for node in self._nodes:
            node.parent = None

        self._viewer = None
        self._view = None
        self._canvas = None
        self._attached = False

    def setVisible(self, value):
        for node in self._nodes:
            node.visible = value

        self._visible = value

    def show(self):
        self.setVisible(True)

    def hide(self):
        self.setVisible(False)

    def _get_center_line_p1(self, pos, line_length, vertical):
        if vertical:
            return [pos[0], pos[1] - line_length / 2, 0]
        else:
            return [pos[0] - line_length / 2, pos[1], 0]

    def _get_center_line_p2(self, pos, line_length, vertical):
        if vertical:
            return [pos[0], pos[1] + line_length / 2, 0]
        else:
            return [pos[0] + line_length / 2, pos[1], 0]


class VispyROIVisual(VispyBaseVisual):
    sigROIChanged = QtCore.Signal(object, object)

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = np.array(value, dtype=float)
        self._update_visual()
        self.sigROIChanged.emit(self.position, self.size)

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, value):
        self._size = np.clip(np.array(value, dtype=float), 1, None)
        self._update_visual()
        self.sigROIChanged.emit(self.position, self.size)

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = float(value)
        self._update_visual()
        self.sigROIChanged.emit(self.position, self.size)

    @property
    def center(self):
        return self._position + 0.5 * self._size

    @property
    def bounds(self):
        corners = self.getCorners()
        x0 = int(np.floor(np.min(corners[:, 0])))
        y0 = int(np.floor(np.min(corners[:, 1])))
        x1 = int(np.ceil(np.max(corners[:, 0])))
        y1 = int(np.ceil(np.max(corners[:, 1])))
        return x0, y0, x1, y1

    def __init__(
        self,
        rect_color='yellow',
        handle_color='orange',
        rotate_handle_color='cyan'
    ):
        super().__init__()

        self._drag_mode = None
        self._world_scale = 1

        self._position = np.array([0, 0], dtype=float)
        self._size = np.array([64, 64], dtype=float)
        self._angle = 0.0

        self._rect_color = Color(rect_color)
        self._handle_color = Color(handle_color)
        self._rotate_handle_color = Color(rotate_handle_color)

        self._handle_side_length = 16
        self._rotate_handle_distance = 32

    def attach(self, viewer, view, canvas, parent=None, order=0):
        super().attach(viewer, view, canvas, parent, order)

        self.rect_node = Compound(
            [Line(connect='segments', method='gl', width=4)],
            parent=parent,
        )
        self.rect_node.transform = STTransform()
        self.rect_node.order = order

        self.handle_node = Compound(
            [Line(connect='segments', method='gl', width=2)],
            parent=parent,
        )
        self.handle_node.transform = STTransform()
        self.handle_node.order = order

        self.rotate_handle_node = Compound(
            [Line(connect='segments', method='gl', width=2)],
            parent=parent,
        )
        self.rotate_handle_node.transform = STTransform()
        self.rotate_handle_node.order = order

        self.rotate_line_node = Compound(
            [Line(connect='segments', method='gl', width=2)],
            parent=parent,
        )
        self.rotate_line_node.transform = STTransform()
        self.rotate_line_node.order = order

        self._nodes = [
            self.rect_node,
            self.handle_node,
            self.rotate_handle_node,
            self.rotate_line_node,
        ]

        canvas.connect(self.on_mouse_press)
        canvas.connect(self.on_mouse_move)
        canvas.connect(self.on_mouse_release)

        self._viewer.camera.events.zoom.connect(self._on_zoom_change)
        self._viewer.dims.events.ndisplay.connect(self._on_data_change)

        self._on_zoom_change(None)
        self._on_data_change(None)
        self._update_visual()

    def setVisible(self, value):
        super().setVisible(value)
        self._on_data_change(None)

    def getCorners(self):
        x0, y0 = self._position
        width, height = self._size

        corners = np.array([
            [x0, y0],
            [x0 + width, y0],
            [x0 + width, y0 + height],
            [x0, y0 + height],
        ], dtype=float)

        return self._rotate_points(corners)

    def _rotate_points(self, points):
        center = self.center
        angle_rad = np.deg2rad(self._angle)

        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        shifted = np.asarray(points, dtype=float) - center

        rotated = np.empty_like(shifted)
        rotated[:, 0] = shifted[:, 0] * cos_a - shifted[:, 1] * sin_a
        rotated[:, 1] = shifted[:, 0] * sin_a + shifted[:, 1] * cos_a

        return rotated + center

    def _world_to_local(self, point):
        center = self.center
        angle_rad = np.deg2rad(-self._angle)

        cos_a = np.cos(angle_rad)
        sin_a = np.sin(angle_rad)

        shifted = np.asarray(point, dtype=float) - center

        local = np.empty_like(shifted)
        local[0] = shifted[0] * cos_a - shifted[1] * sin_a
        local[1] = shifted[0] * sin_a + shifted[1] * cos_a

        return local + center

    def _line_data_from_points(self, points, closed=True):
        points = np.asarray(points, dtype=float)

        if closed:
            pairs = [
                points[0], points[1],
                points[1], points[2],
                points[2], points[3],
                points[3], points[0],
            ]
        else:
            pairs = [points[0], points[1]]

        data = np.zeros((len(pairs), 3), dtype=float)
        data[:, 0:2] = np.asarray(pairs)
        return data

    def _square_data(self, center, side_length):
        half = 0.5 * side_length
        x, y = center

        points = np.array([
            [x - half, y - half],
            [x + half, y - half],
            [x + half, y + half],
            [x - half, y + half],
        ], dtype=float)

        return self._line_data_from_points(points, closed=True)

    def _update_visual(self):
        if not self._attached:
            return

        corners = self.getCorners()
        rect_data = self._line_data_from_points(corners, closed=True)

        self.rect_node._subvisuals[0].set_data(
            rect_data,
            self._rect_color
        )

        handle_size = self._handle_side_length * self._world_scale

        # Resize handle: bottom-right corner of the rotated ROI.
        resize_handle_center = corners[2]
        resize_handle_data = self._square_data(
            resize_handle_center,
            handle_size
        )

        self.handle_node._subvisuals[0].set_data(
            resize_handle_data,
            self._handle_color
        )

        # Hide the separate rotation handle.
        # Rotation is controlled with Shift + drag on the orange handle.
        empty_data = np.zeros((0, 3), dtype=float)

        self.rotate_line_node._subvisuals[0].set_data(
            empty_data,
            self._rotate_handle_color
        )
        self.rotate_handle_node._subvisuals[0].set_data(
            empty_data,
            self._rotate_handle_color
        )

    def _update_position(self):
        self._update_visual()

    def _update_size(self):
        self._update_visual()

    def _update_handle(self):
        self._update_visual()

    def _on_data_change(self, event):
        if not self._attached or not self._visible:
            return

        ndisplay = len(self._viewer.dims.displayed)
        if ndisplay != 2:
            raise ValueError('ndisplay not supported')

        self._update_visual()

    def _on_zoom_change(self, event):
        if not self._attached:
            return

        self._world_scale = 1 / self._viewer.camera.zoom
        self._update_visual()

    def on_mouse_press(self, event):
        if not self._visible or event.button != 1:
            return

        mouse_pos = np.array(
            self._view.scene.node_transform(self._view).imap(event.pos)[0:2]
        )

        mouse_local = self._world_to_local(mouse_pos)

        x0, y0 = self._position
        width, height = self._size
        x1 = x0 + width
        y1 = y0 + height

        handle_size = self._handle_side_length * self._world_scale
        half_handle = 0.5 * handle_size

        resize_handle_local = np.array([x1, y1], dtype=float)

        if (
                abs(mouse_local[0] - resize_handle_local[0]) <= half_handle and
                abs(mouse_local[1] - resize_handle_local[1]) <= half_handle
        ):
            modifiers = getattr(event, "modifiers", ())
            shift_pressed = any(
                "shift" in str(modifier).lower()
                for modifier in modifiers
            )

            if shift_pressed:
                self._drag_mode = 'rotate'
            else:
                self._drag_mode = 'scale'

        elif (
            x0 <= mouse_local[0] <= x1 and
            y0 <= mouse_local[1] <= y1
        ):
            self._drag_mode = 'move'

        else:
            return

        self._view.interactive = False

        self._start_move_visual_pos = self.position.copy()
        self._start_move_visual_size = self.size.copy()
        self._start_move_visual_angle = self.angle
        self._start_move_mouse_pos = mouse_pos
        self._start_move_mouse_local = mouse_local
        self._start_move_center = self.center.copy()

        if self._drag_mode == 'rotate':
            delta = mouse_pos - self._start_move_center
            self._start_rotation_mouse_angle = np.rad2deg(
                np.arctan2(delta[1], delta[0])
            )

    def on_mouse_move(self, event):
        if not self._visible or self._drag_mode is None:
            return

        mouse_pos = np.array(
            self._view.scene.node_transform(self._view).imap(event.pos)[0:2]
        )

        if self._drag_mode == 'move':
            self.position = np.rint(
                self._start_move_visual_pos +
                mouse_pos -
                self._start_move_mouse_pos
            )

        elif self._drag_mode == 'scale':
            mouse_local = self._world_to_local(mouse_pos)
            delta_local = mouse_local - self._start_move_mouse_local

            self.size = np.rint(
                np.clip(
                    self._start_move_visual_size + delta_local,
                    1,
                    None
                )
            )

        elif self._drag_mode == 'rotate':
            delta = mouse_pos - self._start_move_center
            current_mouse_angle = np.rad2deg(
                np.arctan2(delta[1], delta[0])
            )

            self.angle = (
                self._start_move_visual_angle +
                current_mouse_angle -
                self._start_rotation_mouse_angle
            )

    def on_mouse_release(self, event):
        if not self._visible or event.button != 1:
            return

        self._view.interactive = True
        self._drag_mode = None


class VispyLineVisual(VispyBaseVisual):
    sigPositionChanged = QtCore.Signal(np.ndarray, int)

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, value):
        self._position = np.array(value, dtype=int)
        self._update_position()

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = value
        self._update_angle()

    def __init__(self, color='yellow', movable=False):
        super().__init__()
        self._drag_mode = None
        self._world_scale = 1

        self._position = [0, 0]
        self._angle = 0.0

        self._color = Color(color)
        self._movable = movable
        self._click_sensitivity = 16

        # note order is x, y, z for VisPy
        self._line_data2D = np.array(
            [[0, 0, 0], [1, 0, 0]]
        )
        self._line_length = 4096

    def attach(self, viewer, view, canvas, parent=None, order=0):
        super().attach(viewer, view, canvas, parent, order)

        self.node = Compound(
            [Line(connect='segments', method='gl', width=4)],
            parent=parent,
        )
        self.node.transform = STTransform()
        self.node.order = order

        self._nodes = [self.node]

        canvas.connect(self.on_mouse_press)
        canvas.connect(self.on_mouse_move)
        canvas.connect(self.on_mouse_release)
        self._viewer.camera.events.zoom.connect(self._on_zoom_change)
        self._viewer.dims.events.ndisplay.connect(self._on_data_change)

        self._on_zoom_change(None)
        self._on_data_change(None)
        self._update_position()

    def setVisible(self, value):
        super().setVisible(value)
        self._on_data_change(None)

    def _update_position(self):
        if not self._attached:
            return

        angleRad = np.deg2rad(self._angle)
        self.node.transform.translate = [
            self._position[0] - self._line_length / 2 * self._world_scale * (np.cos(angleRad)),
            self._position[1] - self._line_length / 2 * self._world_scale * (np.sin(angleRad)),
            0, 0
        ]

    def _update_angle(self):
        if not self._attached:
            return

        self._line_data2D = np.array(
            [
                [0, 0, 0],
                [self._world_scale * self._line_length * np.cos(np.deg2rad(self._angle)),
                 self._world_scale * self._line_length * np.sin(np.deg2rad(self._angle)),
                 0]
            ]
        )
        self._on_data_change(None)
        self._update_position()

    def _on_data_change(self, event):
        if not self._attached or not self._visible:
            return

        # Actual number of displayed dims
        ndisplay = len(self._viewer.dims.displayed)
        if ndisplay != 2:
            raise ValueError('ndisplay not supported')

        self.node._subvisuals[0].set_data(self._line_data2D, self._color)

    def _on_zoom_change(self, event):
        if not self._attached:
            return

        self._world_scale = 1 / self._viewer.camera.zoom
        self._update_angle()

    def on_mouse_press(self, event):
        if not self._visible or not self._movable or event.button != 1:
            return

        # Determine whether the line was clicked
        mouse_pos = np.array(self._view.scene.node_transform(self._view).imap(event.pos)[0:2])

        s = np.sin(np.deg2rad(-self.angle))
        c = np.cos(np.deg2rad(-self.angle))

        center = np.array(self.position)

        mouse_pos_rot = mouse_pos - center
        mouse_pos_rot = np.array([mouse_pos_rot[0] * c - mouse_pos_rot[1] * s,
                                  mouse_pos_rot[0] * s + mouse_pos_rot[1] * c])
        mouse_pos_rot = mouse_pos_rot + center

        x_start = self.position[0] - self._line_length / 2
        x_end = self.position[0] + self._line_length / 2
        y_start = self.position[1] - self._click_sensitivity * self._world_scale
        y_end = self.position[1] + self._click_sensitivity * self._world_scale

        if x_start <= mouse_pos_rot[0] <= x_end and y_start <= mouse_pos_rot[1] <= y_end:
            self._drag_mode = 'move'
        else:
            return

        # Prepare for dragging
        self._view.interactive = False
        self._start_move_visual_pos = self.position
        self._start_move_mouse_pos = mouse_pos

    def on_mouse_move(self, event):
        if not self._visible or not self._movable or self._drag_mode is None:
            return

        mouse_pos = self._view.scene.node_transform(self._view).imap(event.pos)[0:2]
        if self._drag_mode == 'move':
            self.position = np.rint(
                self._start_move_visual_pos + mouse_pos - self._start_move_mouse_pos
            )

    def on_mouse_release(self, event):
        if not self._visible or not self._movable or event.button != 1:
            return

        self._view.interactive = True
        self._drag_mode = None


class VispyGridVisual(VispyBaseVisual):
    def __init__(self, color='yellow'):
        super().__init__()
        self._color = Color(color).rgba
        self._shape = np.array([0, 0])
        self._line_data2D = None
        self._line_length = 4096

    def attach(self, viewer, view, canvas, parent=None, order=0):
        super().attach(viewer, view, canvas, parent, order)

        self._update_line_data()

        self.node = Compound(
            [Line(connect='segments', method='gl', width=4)],
            parent=parent,
        )
        self.node.transform = STTransform()
        self.node.order = order

        self._nodes = [self.node]

        self._viewer.camera.events.zoom.connect(self._on_zoom_change)
        self._viewer.dims.events.ndisplay.connect(self._on_data_change)

        self._on_data_change(None)

    def setVisible(self, value):
        super().setVisible(value)
        self._on_data_change(None)

    def update(self, shape):
        self._shape = np.array(shape)
        self._update_line_data()

    def _update_line_data(self):
        scaled_line_length = self._line_length / self._viewer.camera.zoom
        self._line_data2D = np.array(
            [
                self._get_center_line_p1(0.25 * self._shape, scaled_line_length, True),
                self._get_center_line_p2(0.25 * self._shape, scaled_line_length, True),
                self._get_center_line_p1(0.375 * self._shape, scaled_line_length, True),
                self._get_center_line_p2(0.375 * self._shape, scaled_line_length, True),
                self._get_center_line_p1(0.50 * self._shape, scaled_line_length, True),
                self._get_center_line_p2(0.50 * self._shape, scaled_line_length, True),
                self._get_center_line_p1(0.625 * self._shape, scaled_line_length, True),
                self._get_center_line_p2(0.625 * self._shape, scaled_line_length, True),
                self._get_center_line_p1(0.75 * self._shape, scaled_line_length, True),
                self._get_center_line_p2(0.75 * self._shape, scaled_line_length, True),

                self._get_center_line_p1(0.25 * self._shape, scaled_line_length, False),
                self._get_center_line_p2(0.25 * self._shape, scaled_line_length, False),
                self._get_center_line_p1(0.375 * self._shape, scaled_line_length, False),
                self._get_center_line_p2(0.375 * self._shape, scaled_line_length, False),
                self._get_center_line_p1(0.50 * self._shape, scaled_line_length, False),
                self._get_center_line_p2(0.50 * self._shape, scaled_line_length, False),
                self._get_center_line_p1(0.625 * self._shape, scaled_line_length, False),
                self._get_center_line_p2(0.625 * self._shape, scaled_line_length, False),
                self._get_center_line_p1(0.75 * self._shape, scaled_line_length, False),
                self._get_center_line_p2(0.75 * self._shape, scaled_line_length, False)
            ]
        )
        self._on_data_change(None)

    def _on_data_change(self, event):
        if not self._attached or not self._visible or self._line_data2D is None:
            return

        # Actual number of displayed dims
        ndisplay = len(self._viewer.dims.displayed)
        if ndisplay != 2:
            raise ValueError('ndisplay not supported')

        self.node._subvisuals[0].set_data(self._line_data2D, self._color)

    def _on_zoom_change(self, event):
        if not self._attached:
            return

        self._update_line_data()


class VispyCrosshairVisual(VispyBaseVisual):
    def __init__(self, color='yellow'):
        super().__init__()
        self._paused = False
        self._mouse_moved_since_press = False
        self._color = Color(color).rgba
        self._line_positions = [0, 0]
        self._line_data2D = None
        self._line_length = 4096

    def attach(self, viewer, view, canvas, parent=None, order=0):
        super().attach(viewer, view, canvas, parent, order)

        self._update_line_data()

        self.node = Compound(
            [Line(connect='segments', method='gl', width=4)],
            parent=parent,
        )
        self.node.transform = STTransform()
        self.node.order = order

        self._nodes = [self.node]

        try:
            canvas.connect(self.on_mouse_press)
            canvas.connect(self.on_mouse_move)
            canvas.connect(self.on_mouse_release)
        except Exception as e:
            print(f'Error connecting to canvas: {e}')
        self._viewer.camera.events.zoom.connect(self._on_zoom_change)
        self._viewer.dims.events.ndisplay.connect(self._on_data_change)

        self._on_data_change(None)

    def setVisible(self, value):
        super().setVisible(value)
        self._on_data_change(None)

    def _update_line_data(self):
        scaled_line_length = self._line_length / self._viewer.camera.zoom
        self._line_data2D = np.array(
            [
                self._get_center_line_p1(self._line_positions, scaled_line_length, True),
                self._get_center_line_p2(self._line_positions, scaled_line_length, True),
                self._get_center_line_p1(self._line_positions, scaled_line_length, False),
                self._get_center_line_p2(self._line_positions, scaled_line_length, False)
            ]
        )
        self._on_data_change(None)

    def _on_data_change(self, event):
        if not self._attached or not self._visible or self._line_data2D is None:
            return

        # Actual number of displayed dims
        ndisplay = len(self._viewer.dims.displayed)
        if ndisplay != 2:
            raise ValueError('ndisplay not supported')

        self.node._subvisuals[0].set_data(self._line_data2D, self._color)

    def _on_zoom_change(self, event):
        if not self._attached:
            return

        self._update_line_data()

    def on_mouse_press(self, event):
        if event.button != 1 or not self._visible:
            return

        self._mouse_moved_since_press = False

    def on_mouse_move(self, event):
        self._mouse_moved_since_press = True

        if not self._visible or self._paused:
            return

        mouse_pos = self._view.scene.node_transform(self._view).imap(event.pos)[0:2]
        self._line_positions = [mouse_pos[0], mouse_pos[1]]
        self._update_line_data()

    def on_mouse_release(self, event):
        if event.button != 1 or not self._visible or self._mouse_moved_since_press:
            return

        self._paused = not self._paused
        if not self._paused:
            self.on_mouse_move(event)


class VispyScatterVisual(VispyBaseVisual):
    def __init__(self, color='red', symbol='x'):
        super().__init__()
        self._color = Color(color)
        self._symbol = symbol
        self._markers_data = -1e8 * np.ones((1, 2))

    def attach(self, viewer, view, canvas, parent=None, order=0):
        super().attach(viewer, view, canvas, parent, order)

        self.node = Markers(pos=self._markers_data, parent=parent)
        self.node.transform = STTransform()
        self.node.order = order

        self._nodes = [self.node]

        self._viewer.dims.events.ndisplay.connect(self._on_data_change)

        self._on_data_change(None)

    def setVisible(self, value):
        super().setVisible(value)
        self._on_data_change(None)

    def setData(self, x, y):
        self._markers_data = np.column_stack((x, y))
        self._on_data_change(None)

    def _on_data_change(self, event):
        if not self._attached or not self._visible:
            return

        # Actual number of displayed dims
        ndisplay = len(self._viewer.dims.displayed)
        if ndisplay != 2:
            raise ValueError('ndisplay not supported')

        self.node.set_data(self._markers_data, edge_color=self._color, face_color=self._color,
                           symbol=self._symbol)
