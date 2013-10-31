# coding=UTF-8
# ex:ts=4:sw=4:et=on

# Copyright (c) 2013, Mathijs Dumon
# All rights reserved.
# Complete license can be found in the LICENSE file.

import os

from pyxrd.generic.io.file_parsers import parsers
from pyxrd.generic.controllers import DialogController
from pyxrd.generic.controllers.handlers import float_entry_widget_handler
from pyxrd.generic.plot.controllers import EyedropperCursorPlot

class PatternActionController(DialogController):
    """
        General class for actions that can be applied on ExperimentalPattern
        models.
        
        Attributes:
         model_setup_method: the name of the method to call on the model to
          auto-setup any variables for the action. Optional; can be None.
        model_action_method: the name of the method to call on the model when
         the user decides to apply the action. Required, cannot be None.
        model_cancel_method: the name of the method to call on the model when
         the user decides to cancel the action. Optional; can be None.
    """
    model_setup_method = None
    model_action_method = None
    model_cancel_method = None

    def register_adapters(self):
        if self.model_setup_method != None:
            getattr(self.model, self.model_setup_method)()
        return super(PatternActionController, self).register_adapters()

    # ------------------------------------------------------------
    #      GTK Signal handlers
    # ------------------------------------------------------------
    def on_btn_ok_clicked(self, event):
        try: getattr(self.model, self.model_action_method)()
        except:
            raise ValueError, "Subclasses of PatternActionController should specify a valid action method name!"
        return super(PatternActionController, self).on_btn_ok_clicked(event)

    def on_cancel(self):
        if self.model_cancel_method != None:
            getattr(self.model, self.model_cancel_method)()
        return super(PatternActionController, self).on_cancel()

    pass # end of class

class AddNoiseController(PatternActionController):
    """
        Controller for the experimental pattern 'add noise' action view.
    """

    auto_adapt_included = [
        "noise_fraction",
    ]
    model_setup_method = None
    model_action_method = "add_noise"
    model_cancel_method = "clear_noise_variables"

    pass # end of class


class ShiftDataController(PatternActionController):
    """
        Controller for the experimental pattern 'shift data' action view.
    """
    auto_adapt_included = [
        "shift_value",
        "shift_position",
    ]
    model_setup_method = "find_shift_value"
    model_action_method = "shift_data"
    model_cancel_method = "clear_shift_variables"

    pass # end of class

class SmoothDataController(PatternActionController):

    auto_adapt_included = [
        "smooth_type",
        "smooth_degree",
    ]
    model_setup_method = "setup_smooth_variables"
    model_action_method = "smooth_data"
    model_cancel_method = "clear_smooth_variables"

    pass # end of class

class StripPeakController(PatternActionController):

    auto_adapt_included = [
        "strip_startx",
        "strip_endx",
        "noise_level"
    ]
    model_setup_method = None
    model_action_method = "strip_peak"
    model_cancel_method = "clear_strip_variables"

    # ------------------------------------------------------------
    #      GTK Signal handlers
    # ------------------------------------------------------------
    def on_sample_start_clicked(self, event):
        self.sample("strip_startx")
        return True

    def on_sample_end_clicked(self, event):
        self.sample("strip_endx")
        return True

    def sample(self, attribute):

        def onclick(edc, x_pos, event):
            if edc != None:
                edc.enabled = False
                edc.disconnect()
            if x_pos != -1:
                setattr(self.model, attribute, x_pos)
            self.view.get_toplevel().present()
            del self.edc

        self.edc = EyedropperCursorPlot(
            self.parent.parent.plot_controller.figure,
            self.parent.parent.plot_controller.canvas,
            self.parent.parent.plot_controller.canvas.get_window(),
            onclick,
            True, True
        )

        self.view.get_toplevel().hide()
        self.parent.parent.view.get_toplevel().present()

    pass # end of class

class BackgroundController(PatternActionController):
    """
        Controller for the experimental pattern 'remove background' action view.
    """

    file_filters = [parser.file_filter for parser in parsers["xrd"]]
    auto_adapt_included = [
        "bg_type",
        "bg_position",
        "bg_scale",
    ]
    model_setup_method = "find_bg_position"
    model_action_method = "remove_background"
    model_cancel_method = "clear_bg_variables"

    def register_adapters(self):
        # Add duplicate entry
        # FIXME in the future, this better become a separate view ...?
        float_entry_widget_handler(
            self,
            self.model.get_prop_intel_by_name("bg_position"),
            self.view['bg_offset']
        )
        super(BackgroundController, self).register_adapters()

    def register_view(self, view):
        super(BackgroundController, self).register_view(view)
        view.set_file_dialog(
            self.get_load_dialog(
                title="Open XRD file for import",
                parent=view.get_top_widget()
            ),
            self.on_pattern_file_set
        )
        view.select_bg_view(self.model.get_bg_type_lbl().lower())

    # ------------------------------------------------------------
    #      Notifications of observable properties
    # ------------------------------------------------------------
    @PatternActionController.observe("bg_type", assign=True)
    def notif_bg_type_changed(self, model, prop_name, info):
        self.view.select_bg_view(self.model.get_bg_type_lbl().lower())
        return

    # ------------------------------------------------------------
    #      GTK Signal handlers
    # ------------------------------------------------------------
    def on_pattern_file_set(self, dialog):
        # TODO
        # This should allow more flexibility:
        #  Patterns should be allowed to not have the exact same shape,
        #  add an x-shift variable to align them
        filename = dialog.get_filename()
        parser = dialog.get_filter().get_data("parser")
        data_objects = None
        try:
            data_objects = parser.parse(filename)
            pattern = data_objects[0].data
            bg_pattern_x = pattern[:, 0].copy()
            bg_pattern_y = pattern[:, 1].copy()
            del pattern

            if bg_pattern_x.shape != self.model.xy_store._model_data_x.shape:
                raise ValueError, "Shape mismatch: background pattern (shape = %s) and experimental data (shape = %s) need to have the same length!" % (bg_pattern_x.shape, self.model.xy_store._model_data_x.shape)
                dialog.unselect_filename(filename)
            else:
                self.model.bg_pattern = bg_pattern_y
        except Exception as msg:
            message = "An unexpected error has occured when trying to parse %s:\n\n<i>" % os.path.basename(filename)
            message += str(msg) + "</i>\n\n"
            message += "This is most likely caused by an invalid or unsupported file format."
            self.run_information_dialog(
                message=message,
                parent=self.view.get_top_widget()
            )

    pass # end of class