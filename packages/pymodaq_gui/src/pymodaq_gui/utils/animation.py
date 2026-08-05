# Adapted from https://github.com/spyder-ide/qtawesome
import math
from qtpy.QtCore import QTimer, QRect, QPoint, Qt
from qtpy.QtGui import QColor, QPixmap, QPainter, QIcon


# Utility functions for common animation patterns
def _sine_wave_value(elapsed, period, min_val, max_val):
    """Map elapsed time to sine wave value between min and max.

    Args:
        elapsed: Elapsed time in milliseconds
        period: Period of one complete sine wave cycle in milliseconds
        min_val: Minimum value (at sine wave minimum)
        max_val: Maximum value (at sine wave maximum)

    Returns:
        Value between min_val and max_val based on sine wave
    """
    angle = (elapsed % period) / period * 2 * math.pi
    sine = math.sin(angle)
    value_range = max_val - min_val
    return min_val + (sine + 1) / 2 * value_range


def _cosine_wave_value(elapsed, period, min_val, max_val):
    """Map elapsed time to cosine wave value between min and max.

    Similar to sine but starts at maximum value.

    Args:
        elapsed: Elapsed time in milliseconds
        period: Period of one complete cosine wave cycle in milliseconds
        min_val: Minimum value (at cosine wave minimum)
        max_val: Maximum value (at cosine wave maximum)

    Returns:
        Value between min_val and max_val based on cosine wave
    """
    angle = (elapsed % period) / period * 2 * math.pi
    cosine = math.cos(angle)
    value_range = max_val - min_val
    return min_val + (cosine + 1) / 2 * value_range


def _get_cycle_position(elapsed, period):
    """Get normalized position in current cycle.

    Args:
        elapsed: Elapsed time in milliseconds
        period: Period of one complete cycle in milliseconds

    Returns:
        Float between 0.0 and 1.0 representing position in cycle
    """
    return (elapsed % period) / period


def _elastic_ease_out(t, amplitude=1.0, period_factor=0.3):
    """Elastic ease-out easing function.

    Creates overshoot and bounce effect.

    Args:
        t: Progress value from 0.0 to 1.0
        amplitude: Amplitude of the elastic effect (default: 1.0)
        period_factor: Period factor for oscillation (default: 0.3)

    Returns:
        Eased value with elastic overshoot
    """
    if t == 0 or t == 1:
        return t

    p = period_factor
    s = p / 4
    return amplitude * math.pow(2, -10 * t) * math.sin((t - s) * (2 * math.pi) / p) + 1

# Utility functions for common transformations
def _apply_centered_transform(painter, rect, scale=1.0, angle=0.0):
    """Apply centered transformation to painter.

    Parameters
    ----------
    painter: QPainter
        Painter object
    rect: QRect
        Rectangle containing the icon
    scale: float
        Scale factor
    angle: float
        Rotation angle in degrees
    """
    x_center = rect.width() * 0.5
    y_center = rect.height() * 0.5
    painter.translate(x_center, y_center)
    if angle != 0:
        painter.rotate(angle)
    if scale != 1.0:
        painter.scale(scale, scale)
    painter.translate(-x_center, -y_center)

class BaseAnimation:
    """Base class for all icon animations.

    Provides common functionality like timing, duration, and lifecycle management.
    Subclasses should override _update_animation_state() and _apply_transform().

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 10)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(self, parent_widget, interval=10, duration=None, autostart=True,
                 update_callback=None):
        self.parent_widget = parent_widget
        self.interval = interval
        self.duration = duration
        self.autostart = autostart
        self._update_callback = update_callback

        # Store animation state per widget: [timer, elapsed_time, state_dict]
        self.info = {}

    def _update(self):
        """Internal update method called by timer."""
        if self.parent_widget in self.info:
            timer, elapsed, state = self.info[self.parent_widget]

            # Update elapsed time
            elapsed += self.interval

            # Check if duration has been reached
            if self.duration is not None and elapsed >= self.duration:
                self.stop()
                return

            # Update animation-specific state
            self._update_animation_state(elapsed, state)

            self.info[self.parent_widget] = timer, elapsed, state
            if self._update_callback is not None:
                self._update_callback()
            else:
                self.parent_widget.update()

    def _update_animation_state(self, elapsed, state):
        """Override this method to update animation-specific state.

        Args:
            elapsed: Elapsed time in milliseconds
            state: Dictionary containing animation state
        """
        raise NotImplementedError("Subclasses must implement _update_animation_state")

    def _apply_transform(self, painter, rect, state):
        """Override this method to apply painter transformations.

        Args:
            painter: QPainter object
            rect: QRect defining the icon area
            state: Dictionary containing animation state
        """
        raise NotImplementedError("Subclasses must implement _apply_transform")

    def _get_initial_state(self):
        """Override this method to provide initial animation state.

        Returns:
            Dictionary containing initial animation state
        """
        return {}

    def render_frame(self, base_icon, size) -> QIcon:
        """Render the current animation state into a QIcon.

        Reads the state stored in ``info[parent_widget]`` — call :meth:`init`
        first so the state dict exists.

        Parameters
        ----------
        base_icon:
            The ``QIcon`` to draw as the base image.
        size:
            ``QSize`` for the output pixmap.
        """
        key = self.parent_widget
        state = self.info[key][2] if key in self.info else self._get_initial_state()
        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        if painter.isActive():
            rect = QRect(QPoint(0, 0), size)
            self._apply_transform(painter, rect, state)
            base_icon.paint(painter, rect, Qt.AlignmentFlag.AlignCenter)
            painter.end()
        return QIcon(pm)

    def init(self) -> None:
        """Initialise the timer for this animation.

        Sets ``parent_widget`` as the ``QTimer`` owner and stores initial state
        in ``info[parent_widget]``.  Must be called after setting
        ``parent_widget`` and ``_update_callback``.
        """
        if self.parent_widget not in self.info:
            timer = QTimer(self.parent_widget)
            timer.timeout.connect(self._update)
            self.info[self.parent_widget] = [timer, 0, self._get_initial_state()]
            if self.autostart:
                timer.start(self.interval)

    def start(self):
        """Start the animation."""
        if self.parent_widget in self.info:
            timer = self.info[self.parent_widget][0]
            timer.start(self.interval)

    def stop(self):
        """Stop the animation."""
        if self.parent_widget in self.info:
            timer = self.info[self.parent_widget][0]
            timer.stop()

    def reset(self):
        """Reset animation to initial state."""
        if self.parent_widget in self.info:
            timer = self.info[self.parent_widget][0]
            self.info[self.parent_widget] = [timer, 0, self._get_initial_state()]


class Spin(BaseAnimation):
    """Continuous rotation animation.

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 10)
        step: Rotation increment per update in degrees (default: 1)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self, parent_widget, interval=10, step=1, duration=None, autostart=True
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.step = step

    def _get_initial_state(self):
        return {"angle": 0}

    def _update_animation_state(self, elapsed, state):
        state["angle"] += self.step
        if state["angle"] >= 360:
            state["angle"] = 0

    def _apply_transform(self, painter, rect, state):
        _apply_centered_transform(painter, rect, angle=state["angle"])



class Pulse(Spin):
    """Stepped rotation animation (45-degree increments).

    Args:
        parent_widget: The widget containing the animated icon
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(self, parent_widget, duration=None, autostart=True):
        super().__init__(
            parent_widget, interval=300, step=45, duration=duration, autostart=autostart
        )


class Breathe(BaseAnimation):
    """Breathing/scaling animation (icon grows and shrinks).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        min_scale: Minimum scale factor (default: 0.8)
        max_scale: Maximum scale factor (default: 1.2)
        period: Period in milliseconds for one complete breath cycle (default: 2000)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        min_scale=0.8,
        max_scale=1.2,
        period=2000,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.period = period

    def _get_initial_state(self):
        return {"scale": 1.0}

    def _update_animation_state(self, elapsed, state):
        # Use sine wave for smooth breathing effect
        state["scale"] = _sine_wave_value(
            elapsed, self.period, self.min_scale, self.max_scale
        )

    def _apply_transform(self, painter, rect, state):
        _apply_centered_transform(painter, rect, scale=state["scale"])



class Fade(BaseAnimation):
    """Fade/opacity pulsating animation (icon fades in and out).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        min_opacity: Minimum opacity (0.0 to 1.0, default: 0.2)
        max_opacity: Maximum opacity (0.0 to 1.0, default: 1.0)
        period: Period in milliseconds for one complete fade cycle (default: 2000)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)

    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        min_opacity=0.2,
        max_opacity=1.0,
        period=2000,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.min_opacity = max(0.0, min(1.0, min_opacity))
        self.max_opacity = max(0.0, min(1.0, max_opacity))
        self.period = period

    def _get_initial_state(self):
        return {"opacity": 1.0}

    def _update_animation_state(self, elapsed, state):
        # Use sine wave for smooth fading effect
        state["opacity"] = _sine_wave_value(
            elapsed, self.period, self.min_opacity, self.max_opacity
        )

    def _apply_transform(self, painter, rect, state):
        painter.setOpacity(state["opacity"])


class Shake(BaseAnimation):
    """Shake/bounce animation (icon vibrates horizontally and vertically).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        amplitude_x: Horizontal shake amplitude in pixels (default: 3)
        amplitude_y: Vertical shake amplitude in pixels (default: 3)
        period: Period in milliseconds for one complete shake cycle (default: 200)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        amplitude_x=3,
        amplitude_y=3,
        period=200,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.amplitude_x = amplitude_x
        self.amplitude_y = amplitude_y
        self.period = period

    def _get_initial_state(self):
        return {"offset_x": 0, "offset_y": 0}

    def _update_animation_state(self, elapsed, state):
        # Use different frequencies for x and y to create more natural shake
        angle_x = (elapsed % self.period) / self.period * 2 * math.pi
        angle_y = (elapsed % (self.period * 1.3)) / (self.period * 1.3) * 2 * math.pi

        state["offset_x"] = math.sin(angle_x) * self.amplitude_x
        state["offset_y"] = math.sin(angle_y) * self.amplitude_y

    def _apply_transform(self, painter, rect, state):
        painter.translate(state["offset_x"], state["offset_y"])


class ColorCycle(BaseAnimation):
    """Color cycling animation (icon cycles through specified colors).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 50)
        colors: List of color strings to cycle through (default: rainbow colors)
        color_duration: Time to spend on each color in milliseconds (default: 500)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=50,
        colors=None,
        color_duration=500,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        if colors is None:
            # Default rainbow colors
            self.colors = [
                "red",
                "orange",
                "yellow",
                "green",
                "blue",
                "indigo",
                "violet",
            ]
        else:
            self.colors = colors

        self.color_duration = color_duration

    def _get_initial_state(self):
        return {"current_color": QColor(self.colors[0]), "color_index": 0}

    def _update_animation_state(self, elapsed, state):
        # Calculate which color we should be at
        total_cycle_time = len(self.colors) * self.color_duration
        cycle_position = elapsed % total_cycle_time
        color_index = int(cycle_position / self.color_duration)

        if color_index != state["color_index"]:
            state["color_index"] = color_index
            state["current_color"] = QColor(self.colors[color_index])

    def _apply_transform(self, painter, rect, state):
        #TODO Not working
        current_color = state["current_color"]
        painter.setPen(current_color)
        painter.setBrush(current_color)


class HeartBeat(BaseAnimation):
    """HeartBeat animation (double pulse with pause, like a heartbeat).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        min_scale: Minimum scale factor (default: 1.0)
        max_scale: Maximum scale factor during pulse (default: 1.3)
        period: Period in milliseconds for one complete heartbeat cycle (default: 1000)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        min_scale=1.0,
        max_scale=1.3,
        period=1000,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.period = period
        # Calculate timing proportions based on period
        # Pattern: beat1 (15%) + gap (10%) + beat2 (15%) + pause (60%)
        self.beat1_end = self.period * 0.15
        self.gap_end = self.period * 0.25
        self.beat2_end = self.period * 0.40

    def _get_initial_state(self):
        return {"scale": 1.0}

    def _update_animation_state(self, elapsed, state):
        # Calculate position in current cycle
        cycle_pos = elapsed % self.period

        if cycle_pos < self.beat1_end:
            # First beat: scale up then down
            progress = cycle_pos / self.beat1_end
            # Use sin for smooth pulse
            scale_factor = math.sin(progress * math.pi)
            state["scale"] = (
                self.min_scale + (self.max_scale - self.min_scale) * scale_factor
            )
        elif cycle_pos < self.gap_end:
            # Gap between beats
            state["scale"] = self.min_scale
        elif cycle_pos < self.beat2_end:
            # Second beat: scale up then down
            progress = (cycle_pos - self.gap_end) / (self.beat2_end - self.gap_end)
            scale_factor = math.sin(progress * math.pi)
            state["scale"] = (
                self.min_scale + (self.max_scale - self.min_scale) * scale_factor
            )
        else:
            # Pause
            state["scale"] = self.min_scale

    def _apply_transform(self, painter, rect, state):
        _apply_centered_transform(painter, rect, scale=state["scale"])



class Swing(BaseAnimation):
    """Swing animation (pendulum-like rotation back and forth).

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        angle: Maximum swing angle in degrees (±angle, default: 15)
        period: Period in milliseconds for one complete swing cycle (default: 1000)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        angle=15,
        period=1000,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.max_angle = angle
        self.period = period

    def _get_initial_state(self):
        return {"angle": 0}

    def _update_animation_state(self, elapsed, state):
        # Use sine wave for smooth pendulum motion
        state["angle"] = _sine_wave_value(
            elapsed, self.period, -self.max_angle, self.max_angle
        )

    def _apply_transform(self, painter, rect, state):
        _apply_centered_transform(painter, rect, angle=state["angle"])



class Elastic(BaseAnimation):
    """Elastic/bounce animation (scale with overshoot and settle).

    The icon scales up, overshoots, bounces back, and settles at the target scale.
    This creates a spring-like elastic effect.

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        min_scale: Starting scale factor (default: 0.5)
        max_scale: Target scale factor (default: 1.0)
        period: Period in milliseconds for one complete elastic bounce cycle (default: 1500)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        min_scale=0.5,
        max_scale=1.0,
        period=1500,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.min_scale = min_scale
        self.max_scale = max_scale
        self.period = period

    def _get_initial_state(self):
        return {"scale": self.min_scale}

    def _update_animation_state(self, elapsed, state):
        # Elastic easing function with overshoot
        cycle_pos = _get_cycle_position(elapsed, self.period)
        scale_progress = _elastic_ease_out(cycle_pos)
        state["scale"] = (
            self.min_scale + (self.max_scale - self.min_scale) * scale_progress
        )

    def _apply_transform(self, painter, rect, state):
        _apply_centered_transform(painter, rect, scale=state["scale"])



class Travel(BaseAnimation):
    """Traveling/scrolling animation with seamless wrap-around.

    The icon moves continuously in the given direction and wraps from one
    edge back to the opposite edge, so it appears to scroll forever.

    Args:
        parent_widget: The widget containing the animated icon
        interval: Update interval in milliseconds (default: 20)
        direction: 'x' for horizontal, 'y' for vertical, 'xy' for diagonal (default: 'x')
        period: Time in milliseconds for one complete traversal (default: 2000)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)
    """

    def __init__(
        self,
        parent_widget,
        interval=20,
        # direction='x',
        direction=(1.0, 1.0),
        period=2000,
        duration=None,
        autostart=True,
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        if direction == 'x':
            self.direction = (1.0, 0.0)
        elif direction == 'y':
            self.direction = (0.0, 1.0)
        elif direction == 'xy':
            self.direction = (1.0, 1.0)
        else:
            self.direction = direction
        self.period = period

    def _get_initial_state(self):
        return {"frac_x": 0.0, "frac_y": 0.0}

    def _update_animation_state(self, elapsed, state):
        frac = (elapsed % self.period) / self.period
        state["frac_x"] = self.direction[0] * frac
        state["frac_y"] = self.direction[1] * frac
        # if self.direction in ('x', 'xy'):
        #     state["frac_x"] = frac
        # if self.direction in ('y', 'xy'):
        #     # Half-period phase offset makes the diagonal path more interesting
        #     state["frac_y"] = ((elapsed + self.period // 2) % self.period) / self.period

    def _apply_transform(self, painter, rect, state):
        pass  # rendering is handled in render_frame

    def render_frame(self, base_icon, size) -> QIcon:
        """Render with double-paint so the icon wraps seamlessly."""
        key = self.parent_widget
        state = self.info[key][2] if key in self.info else self._get_initial_state()
        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        if painter.isActive():
            w, h = size.width(), size.height()
            painter.setClipRect(0, 0, w, h)

            ox = int(state["frac_x"] * w)
            oy = int(state["frac_y"] * h)

            # Initialize xs and ys with two identical values
            xs = [ox, ox]  # Default: no horizontal wrapping
            ys = [oy, oy]  # Default: no vertical wrapping

            # Modify the second entry based on direction
            if self.direction[0] > 0:  # Moving right
                xs[1] = ox - w  # Copy entering from the left
            elif self.direction[0] < 0:  # Moving left
                xs[1] = ox + w  # Copy entering from the right

            if self.direction[1] > 0:  # Moving down
                ys[1] = oy - h  # Copy entering from the top
            elif self.direction[1] < 0:  # Moving up
                ys[1] = oy + h  # Copy entering from the bottom

            # Draw the icon at paired offsets (avoids extra copies for diagonal movement)
            for dx, dy in zip(xs, ys):
                base_icon.paint(
                    painter,
                    QRect(QPoint(dx, dy), size),
                    Qt.AlignmentFlag.AlignCenter,
                )
        return QIcon(pm)


class CompositeAnimation(BaseAnimation):
    """Composite animation that combines multiple animations.

    This allows you to layer multiple animation effects on a single icon.
    For example, you could combine Spin + Breathe, or Swing + Fade.

    Args:
        parent_widget: The widget containing the animated icon
        animations: List of animation instances to combine
        interval: Update interval in milliseconds (default: 10)
        duration: Total animation duration in milliseconds, None for infinite (default: None)
        autostart: Whether to start animation automatically (default: True)

    Example:
        # Combine spinning and breathing
        anim1 = qta.Spin(button, step=2, autostart=False)
        anim2 = qta.Breathe(button, autostart=False)
        composite = qta.CompositeAnimation(button, [anim1, anim2])
        icon = qta.icon('fa5s.star', animation=composite)
    """

    def __init__(
        self, parent_widget, animations, interval=10, duration=None, autostart=True
    ):
        super().__init__(parent_widget, interval, duration, autostart)
        self.animations = animations

        # Set all child animations to not autostart since we'll manage them
        for anim in self.animations:
            anim.autostart = False
            anim.parent_widget = parent_widget

    def _get_initial_state(self):
        return {"initialized": False}

    def _update_animation_state(self, elapsed, state):
        # Update all child animations' states
        for anim in self.animations:
            if anim.parent_widget in anim.info:
                timer, anim_elapsed, anim_state = anim.info[anim.parent_widget]
                anim_elapsed += self.interval
                anim._update_animation_state(anim_elapsed, anim_state)
                anim.info[anim.parent_widget] = timer, anim_elapsed, anim_state

    def _apply_transform(self, painter, rect, state):
        # Initialize child animations on first call
        if not state["initialized"]:
            for anim in self.animations:
                if anim.parent_widget not in anim.info:
                    # Create a dummy timer (won't be used)
                    from qtpy.QtCore import QTimer

                    timer = QTimer(anim.parent_widget)
                    anim.info[anim.parent_widget] = [
                        timer,
                        0,
                        anim._get_initial_state(),
                    ]
            state["initialized"] = True

        # Apply all child animation transforms
        for anim in self.animations:
            if anim.parent_widget in anim.info:
                timer, anim_elapsed, anim_state = anim.info[anim.parent_widget]
                anim._apply_transform(painter, rect, anim_state)

    def start(self):
        """Start the composite animation and all child animations."""
        super().start()
        for anim in self.animations:
            if anim.parent_widget in anim.info:
                # Child animations don't have active timers, managed by parent
                pass

    def stop(self):
        """Stop the composite animation and all child animations."""
        super().stop()
        for anim in self.animations:
            if anim.parent_widget in anim.info:
                pass
